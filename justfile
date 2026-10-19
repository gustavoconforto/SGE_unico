run:
    uv run manage.py runserver

migrations:
    uv run manage.py makemigrations

migrate:
    uv run manage.py migrate

reset:
    uv run reset_db.py