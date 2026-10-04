#!/bin/sh
set -eu
cd /workspace
tar --no-same-owner --no-same-permissions -xf -
exec "$@"
