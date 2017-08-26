This README is significantly out-of-date and needs to be re-written. Use at
your own risk!




One-time setup:

Ensure you're running from a terminal/shell in a GUI environment that can
launch a web browser

cd to root directory of this project
virtualenv -p python3 venv
. ./venv/bin/activate
pip install -r etc/pip-requirements.txt

To re-generate etc/pip-requirements.txt:
(. ./venv/bin/activate && pip freeze) > etc/pip-requirements.txt

./bin/generate-acls.sh var/acls
# 1) Log in to Google account in web browser if prompted
# 2) Allow app to access/install-into Google driver in web browser if prompted
# 3) Open Google drive in web browser, navigate to the FCCH Membership List
#    folder, right-click the 000 Membership List file, select Open With ->
#    FCCH Access Control, wait for browser to redirect to FCCH website

To run:

cd to root directory of this project
./bin/generate-acls.sh var/acls

Result:
View var/acls/acl-${aclname} e.g. acl-door, acl-big-laser-cutter






systemctl enable $(pwd)/etc/systemd/fcch-access-control-auth-server.service
systemctl disable fcch-access-control-auth-server.service
systemctl start/stop/restart fcch-access-control-auth-server
journalctl -u fcch-access-control-auth-server


systemctl enable $(pwd)/etc/systemd/fcch-access-control-door-controller.service
systemctl disable fcch-access-control-door-controller.service
systemctl start/stop/restart fcch-access-control-door-controller
journalctl -u fcch-access-control-door-controller
