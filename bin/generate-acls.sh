#!/bin/bash

set -e
set -x

script_dir="$(dirname "$0")"
app_dir="$(cd "${script_dir}"/.. && pwd)"

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

. "${app_dir}/venv/bin/activate"
exec python3 "${app_dir}/bin/generate-acls.py" --noauth_local_webserver "$@"
