# Gestão Escolar

School management system for **Único Educacional**. It covers staff, courses,
classes, students and guardians, enrollment contracts and the school's finances
(receivables, payables, installments and payments).

It is a server-rendered Django app. The UI is in Brazilian Portuguese; the code
is in English.

| | |
|---|---|
| Language | Python 3.14 |
| Framework | Django 6.1 |
| Front end | Django templates + htmx 2 + Tailwind CSS 4 + daisyUI 5 (all from CDN) |
| Database | SQLite in development |
| Package manager | [uv](https://docs.astral.sh/uv/) |

## Features

| Area | What you can do |
|---|---|
| Recursos Humanos | Users, groups and permissions (Django auth), employee roles, employees |
| Acadêmico | Courses (programs), school years and their four bimesters, classes, students with their guardians, enrollment contract types, discount types, required documents, enrollments |
| Financeiro | Financial categories, suppliers, accounts receivable, accounts payable, installments, payments |

Creating an enrollment automatically creates its receivable account and
monthly installments. Ending an enrollment early (transferred, dropped,
cancelled) cancels its future open installments. See
[ARCHITECTURE.md](ARCHITECTURE.md#enrollment--finance-workflow).

## Getting started

```bash
# 1. Install dependencies (creates .venv)
uv sync

# 2. Create .env in the project root
cat > .env <<'EOF'
SECRET_KEY=change-me
DJANGO_DEBUG=true
EOF

# 3. Create the database and load reference data
uv run python manage.py migrate
uv run python manage.py clean      # seeds users, programs, school years, classes, etc.

# 4. Run
uv run python manage.py runserver
```

Open http://127.0.0.1:8000/.

`DJANGO_DEBUG=true` is required for now: the database is only configured when
debug is on (see [Known issues](#known-issues)).

### Development users

`manage.py clean` creates two users, both with password `73823789`:

| Username | Role |
|---|---|
| `conforto` | superuser |
| `teste` | staff, non-superuser |

The app pages don't require login yet; these users are for `/admin/`.

## Common commands

```bash
uv run python manage.py test                 # all tests
uv run python manage.py test accounts        # one app
uv run python manage.py makemigrations
uv run python manage.py migrate
uv run python manage.py clean                # (re)seed reference data
uv run python reset_db.py                    # see warning below
```

> **`reset_db.py` is destructive.** It deletes `db.sqlite3` **and every
> migration file** in the project, then regenerates them. Only use it while the
> schema is still throwaway, and never once there's a database you care about.
> Option 2 calls a `seed` command that doesn't exist yet; use option 1.

## Project layout

```
config/        settings, root URLconf, WSGI/ASGI
base/          shared models (Person, TimeStampedModel), search/htmx mixins,
               layout templates, UI components, users/groups/permissions, seed command
employees/     employee roles and employees
programs/      courses
classes/       classes (turmas)
students/      students, guardians and the student↔guardian link
enrollments/   school years, contract types, discounts, required documents, enrollments
accounts/      finance: categories, suppliers, accounts, installments, payments
utils/         small formatting helpers (CPF, CEP, weekend adjustment)
assets/        static files (logo, placeholder images)
media/         uploaded files (student photos)
```

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md): apps, data model, request flow,
  financial rules, design system.
- [CLAUDE.md](CLAUDE.md): conventions for AI coding agents (and a good
  checklist for humans too).

## Known issues

- No authentication on the app's pages: every view is public.
- Production settings are incomplete: `DATABASES` is empty when
  `DJANGO_DEBUG` isn't `true`, and `ALLOWED_HOSTS` is empty.
- Only `accounts` and `enrollments` have tests.
- `pandas` is a dependency but isn't used.
