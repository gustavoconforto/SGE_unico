#!/usr/bin/env bash
{
set -euo pipefail
cd /srv/sge
export PATH="$HOME/.local/bin:$PATH"  # non-interactive SSH skips the profile that adds uv

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
