# Gestão Escolar

School management system for **Único Educacional**. It covers staff, courses,
classes, subjects, students and guardians, enrollment contracts, the school's
finances (receivables, payables, installments and payments) and Bradesco bank
slips.

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
| Acadêmico | Courses (programs), school years and their four bimesters, classes, class roster (active students of a class), subjects, students with their guardians, enrollment contract types, discount types, required documents, enrollments, grade entry and report cards, student incidents (ocorrências), delays and bathroom permissions |
| Financeiro | Financial categories, suppliers, accounts receivable, accounts payable, installments, payments, bank slips (CNAB 400 remittance and return files) |

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
uv run python manage.py seed       # resets the database, then users, classes, staff, students, etc.

# 4. Run
uv run python manage.py runserver
```

Open http://127.0.0.1:8000/.

`DJANGO_DEBUG=true` is required for now: the database is only configured when
debug is on (see [Known issues](#known-issues)).

### Development users

`manage.py seed` creates two users, both with password `73823789`:

| Username | Role |
|---|---|
| `conforto` | superuser |
| `teste` | staff, non-superuser |

Sign in at http://127.0.0.1:8000/login/. The same users work for `/admin/`.

## Common commands

```bash
uv run python manage.py test                 # all tests
uv run python manage.py test accounts        # one app
uv run python manage.py makemigrations
uv run python manage.py migrate
uv run python manage.py seed                 # reset DB; reference data + staff, students and guardians
uv run python manage.py full_seed            # reset DB; a whole school year of data
uv run ruff check <files>                    # lint (the repo isn't clean yet)
uv run ruff format <files>                   # format
```

Both reset the database (drop every table, migrate). `seed` takes
`--students-per-class N` (default 3) and `--random-seed` (default 42).

## Project layout

```
config/        settings, root URLconf, WSGI/ASGI
base/          shared models (Person, TimeStampedModel), search/htmx mixins,
               layout templates, login page, UI components, users/groups/permissions,
               seed and full_seed commands
employees/     employee roles and employees
programs/      courses
classes/       classes (turmas) and the class roster page
grades/        subjects (matérias); grade entry to come
students/      students, guardians and the student↔guardian link
enrollments/   school years, contract types, discounts, required documents, enrollments
accounts/      finance: categories, suppliers, accounts, installments, payments
billing/       Bradesco CNAB 400 bank slips: settings, remittances, returns
utils/         small formatting helpers (CPF, CEP, weekend adjustment)
assets/        static files (logo, favicon, placeholder images)
media/         uploaded files (student photos)
doc/           user manual, in Portuguese
```

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md): apps, data model, request flow,
  financial rules, design system.
- [CLAUDE.md](CLAUDE.md): conventions for AI coding agents (and a good
  checklist for humans too).
- [doc/README.md](doc/README.md): user manual (Portuguese), screen by screen
  and the common workflows.

## Known issues

- Login exists but isn't enforced: every app view is public, and permissions
  aren't checked.
- Production settings are incomplete: `DATABASES` is empty when
  `DJANGO_DEBUG` isn't `true`, and `ALLOWED_HOSTS` is empty.
- `employees`, `programs`, `students` and `grades` have no tests.
