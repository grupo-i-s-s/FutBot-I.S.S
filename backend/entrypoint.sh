#!/bin/sh
set -eu

python -m app.migrate
python -m app.migrate_league_passwords

exec "$@"
