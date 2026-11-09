#!/usr/bin/env bash
{
set -euo pipefail
cd /srv/sge

git pull --ff-only
uv sync --locked

set -a
source /etc/sge/sge.env
set +a

uv run python manage.py migrate --noinput
uv run python manage.py collectstatic --noinput
uv run python manage.py check --deploy

sudo systemctl restart sge
systemctl is-active sge
exit
}
