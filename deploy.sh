#!/usr/bin/env bash
# Redeploy production. Run on the server as the deploy user: /srv/sge/deploy.sh
# Wrapped in { } so bash reads the whole file before `git pull` can rewrite it.
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
