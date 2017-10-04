from __future__ import print_function

import argparse
try:
    import configparser
except:
    import ConfigParser as configparser
import os
import sys
import threading
import time
import traceback
import urllib.parse
import urllib.request

door_controller_dir = os.path.dirname(__file__)
app_dir = os.path.dirname(door_controller_dir)
etc_dir = os.path.join(app_dir, 'etc')

def print_with_timestamp(s):
    print(time.strftime('%Y%m%d %H%M%S'), s)
    # Required for log content to show up in systemd
    sys.stdout.flush()

try:
    import RPi.GPIO as GPIO
except:
    print_with_timestamp('WARNING: import RPi.GPIO failed')
    print_with_timestamp('WARNING: EMULATING all GPIO accesses')
    class GPIO:
        BOARD = 0
        OUT = 0
        HIGH = 0
        LOW = 0

        @classmethod
        def setmode(klass, mode):
            pass

        @classmethod
        def setup(klass, gpio, direction):
            pass

        @classmethod
        def output(klass, gpio, value):
            pass

def to_bool(s):
    return s.lower() in ['true', 'yes', 'on', '1']

class RfidReaderThread(threading.Thread):
    def __init__(self, config):
        super(RfidReaderThread, self).__init__()

        self.reader_type = config['conf']['reader_type']
        self.serial_port = config['conf']['serial_port']
        self.auth_host = config['conf']['auth_host']
        self.auth_port = int(config['conf']['auth_port'])
        self.acl = config['conf']['acl']
        self.gpio = int(config['conf']['gpio'])
        self.allow_retrigger = to_bool(config['conf']['allow_retrigger'])
        self.unlock_period = int(config['conf']['unlock_period'])

        self.relock_timer = None
        self.sw_state_lock = threading.Lock()

    def run(self):
        try:
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup(self.gpio, GPIO.OUT)
            self.lock_door()
            if self.reader_type == 'rdm6300':
                import rdm6300
                rlte = rdm6300.RateLimitTagEvents(self)
                rdr = rdm6300.RDM6300Reader(self.serial_port, rlte)
            elif self.reader_type == 'parallax':
                import parallax_rfid
                rlte = parallax_rfid.RateLimitTagEvents(self)
                rdr = parallax_rfid.ParallaxRfidReader(self.serial_port, rlte)
            else:
                raise Exception('Invalid reader type: ' + self.reader_type)
            rdr.run()
        except:
            print_with_timestamp('EXCEPTION in main loop (exiting):')
            traceback.print_exc()
            sys.exit(1)

    def handle_tag(self, tag, rcv_start_time):
        print_with_timestamp('Tag: ' + repr(tag))

        if not self.validate_tag(tag):
            print_with_timestamp('Ignore; tag not authorized')
            return

        previously_running_timer = None
        with self.sw_state_lock:
            if self.relock_timer:
                # We can't use self.relock_timer without sw_state_lock held,
                # since the timer callback could run and clear
                # self.relock_timer.
                previously_running_timer = self.relock_timer

        if previously_running_timer:
            if not self.allow_retrigger:
                print_with_timestamp('Ignore; door unlocked')
                return
            print_with_timestamp('Restarting lock timer')
            previously_running_timer.cancel()
            # The following join() must happen without sw_state_lock held,
            # since the timer callback can hold that lock, and if we hold it,
            # join() might deadlock waiting for the timer callback to complete,
            # yet it can't complete since we hold the lock.
            previously_running_timer.join()
            self.relock_timer = None

        with self.sw_state_lock:
            self.unlock_door()
            self.relock_timer = threading.Timer(self.unlock_period,
                self.do_scheduled_unlock)
            self.relock_timer.start()

    def handle_data_outside_tag(self, data):
        pass

    def handle_timeout(self, data):
        pass

    def handle_overlong_tag(self, data):
        pass

    def handle_validation_error(self, data):
        pass

    def validate_tag(self, tag):
        try:
            url = 'http://%s:%d/api/check-access-0/%s/%s' % (
                self.auth_host,
                self.auth_port,
                urllib.parse.quote(self.acl),
                urllib.parse.quote(str(tag)))
            with urllib.request.urlopen(url) as f:
                answer = f.read()
                return answer.decode('utf-8') == 'True'
        except:
            print_with_timestamp('EXCEPTION in access check (squashed):')
            traceback.print_exc()
            pass
        return False

    def do_scheduled_unlock(self):
        with self.sw_state_lock:
            self.relock_timer = None
            self.lock_door()

    def unlock_door(self):
        print_with_timestamp('Unlocking door')
        GPIO.output(self.gpio, GPIO.HIGH)

    def lock_door(self):
        print_with_timestamp('Locking door')
        GPIO.output(self.gpio, GPIO.LOW)

config = configparser.ConfigParser()
config.read(etc_dir + '/door-controller.ini')
rfid_reader_thread = RfidReaderThread(config)
rfid_reader_thread.start()
rfid_reader_thread.join()
