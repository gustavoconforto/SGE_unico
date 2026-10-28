# CLAUDE.md

School management system (Django 6.1, Python 3.14, htmx + Tailwind 4 +
daisyUI 5 from CDN, SQLite in dev). Read [ARCHITECTURE.md](ARCHITECTURE.md)
for the data model, financial rules and design system before changing
models, `accounts/` or templates.

## Commands

```bash
uv run python manage.py test               # run after every change
uv run python manage.py test accounts      # single app
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run   # confirm no missing migration
uv run ruff check <files> && uv run ruff format <files>    # only files you touched; the repo isn't ruff-clean yet
uv run python manage.py runserver
uv run python manage.py full_seed          # FLUSHES the database, then fills a whole school year
```

`.env` needs `SECRET_KEY` and `DJANGO_DEBUG=true` (without debug it connects
to PostgreSQL through `DATABASE_URL`). Never run `reset_db.py`: it deletes the
database and all migration files. Ask before running `full_seed` on the dev
database; to try it, point a settings override at a scratch SQLite file.

## Language

- Code, identifiers, comments, docstrings, commit messages: **English**.
- Everything the user sees (labels, `verbose_name`, choices, messages, help
  text, templates): **Brazilian Portuguese**.

## Conventions

### Models
- Money: `DecimalField(**MONEY)` from `accounts/models.py`, `Decimal` math,
  `ZERO` constant. Never float.
- Fixed options: `models.TextChoices` with short codes (`"R"`, `"A"`, `"PIX"`).
- Foreign keys default to `on_delete=PROTECT`. Every field has a Portuguese
  `verbose_name`; every model has `verbose_name(_plural)`, `ordering` and
  `__str__`.
- Integrity rules go in `Meta.constraints` (`UniqueConstraint`,
  `CheckConstraint`), with form validation giving the friendly message.
- People inherit `base.models.Person`; other models with audit dates inherit
  `TimeStampedModel`. CPF/CNPJ/CEP are stored digits only.
- Values that depend on today (overdue, situation) are computed per request,
  never stored.
- Avoid N+1 queries in lists: `select_related`, and queryset annotations like
  `Account.objects.with_installment_summary()` and
  `Installment.objects.with_balance()`.

### Views and URLs
- New views are class-based. Function views in `base/views.py` and the student
  add/edit views are legacy; don't copy them.
- URLs: `<resource>/list|add|edit/<pk>|delete/<pk>/`, names
  `<resource>_list|_add|_edit|_delete`, reversed with the app namespace
  (`reverse_lazy("accounts:supplier_list")`). Register new apps in
  `config/urls.py`.
- Lists: `HtmxSearchMixin` (search only) or `HtmxFilterMixin` (search +
  `filter_form_class`) from `base/search.py`. Set `search_fields`,
  `partial_template_name`, `paginate_by = 10`, `ordering`. Use `filter_lookups`
  for simple lookups and `filter_<field>(self, queryset, value)` methods for
  custom ones.
- Mixins go left of the generic view; a mixin that annotates fields used by a
  filter goes **right** of `HtmxFilterMixin`.
- Flash a message on every write: "Registro cadastrado com sucesso",
  "Registro atualizado com sucesso" (`success`), "Registro deletado com
  sucesso" (`warning`). Reuse `SuccessMessageMixin` / `ProtectedDeleteMixin`
  in `accounts/views.py` for new CRUDs.
- Multi-model writes go in `transaction.atomic()`.
- Student records tied to a school year (grades, incidents, delays, bathroom
  permissions, Q&A sessions, pathway memberships) point at `Enrollment`, not
  `Student`. Their forms use
  `ActiveEnrollmentFormMixin` from `incidents/forms.py` to list only active
  enrollments.
- Prefill from a query param (`?installment=<pk>`, `?account=<pk>`) via
  `get_initial()`, for links from other pages.
- "Pick A, then B filtered by A" screens: copy the class roster
  (`ClassDetailView` + `ClassOptionsView` in `classes/views.py`). The options
  endpoint swaps the second select, clears `#search-results` with
  `hx-swap-oob`, and sets `HX-Push-Url`, so the selection survives a reload.

### Forms
- `ModelForm` with explicit `fields` and widgets carrying the daisyUI classes:
  `input input-neutral w-full`, `select select-neutral w-full`,
  `textarea textarea-neutral w-full`; filter forms use the `-sm` sizes and
  `required=False` with an empty `("", "Todas")` choice.
- Dates: `date_input()` from `accounts/forms.py`.
- Cross-field validation in `clean()` with `add_error(field, "mensagem")`.

### Templates
- Per resource, in `<app>/templates/<resource_plural>/`: `<r>_list.html`,
  `partials/<r>_table.html`, `<r>_form.html`, `<r>_add.html`,
  `<r>_edit.html`, `<r>_delete.html`. Copy an existing set (e.g.
  `accounts/templates/suppliers/`: breadcrumb, sectioned form, sticky save
  bar, row menu with delete dialog) rather than inventing a layout.
- Extend `base/base.html`; fill `page_title` (browser tab), `header`, `content`.
- List page: the table partial lives inside `<div id="search-results">`,
  search uses `components/search/filter_form.html`, the table is
  `<div class="table-wrap"><table class="data-table">` with plain `<th>`/`<td>`,
  the partial ends with `components/table/pagination.html`.
- Use the components: `components/form/field.html` for every field, the
  `components/button/*` buttons (or the `ui-btn` classes), `page/heading.html`,
  `page/breadcrumb.html`, `table/row_menu.html`. Don't hand-roll buttons or
  fields, and don't add colors or fonts: the design system is in
  ARCHITECTURE.md.
- Money `R$ {{ v|floatformat:"2g" }}` right-aligned with `whitespace-nowrap`
  (plain `floatformat:2` inside attributes); dates `|date:"d/m/Y"`; CPF/CNPJ
  `|document` (`{% load ui %}`); badge colors as in ARCHITECTURE.md.
- New screens get a link in the sidebar under the right section. Each section
  is a file in `base/templates/base/sidebar/menu/` (`academico.html`,
  `financeiro.html`, …) included by `sidebar/sidebar.html`; add
  `{% include 'base/sidebar/items/menu_item.html' with path=… label=… icon=… %}`
  with a Material Symbols icon name. Don't edit
  `base/templates/base/sidebar.html`: it's the old, unused copy.

### Finance rules (don't break)
- Use `AccountReceivable` / `AccountPayable` proxies, not raw `Account`, in
  views and forms.
- `Payment.save()`/`delete()` refresh the installment status; don't update
  `Installment.status` by hand except to cancel (or to expire, done by the
  bank return import). Use `PENDING_STATUSES` for "still owed".
- Payment `amount` includes penalty, interest and monetary adjustment;
  principal = amount − charges + discount, and it can't exceed the
  installment balance.
- Bank slips: go through `billing/services.py` (`create_remittance`,
  `write_off_candidates`, `import_return`); never build CNAB lines outside
  `billing/cnab400.py`. A slip the bank registered must be written off
  (movement `02`, confirmed by return `10`) before its installment gets a new
  slip; `LIVE_SLIP_STATUSES` enforces this.
- Enrollment creation generates the account and installments through the
  `post_save` signal in `enrollments/signals.py`; don't duplicate that in views.

### Lessons rules
- Lessons run Monday to Saturday: 12 periods a day Monday to Friday, 7 on
  Saturday. Build a day's periods with `weekday_periods(weekday)` from
  `lessons/models.py`, not `PERIODS` (which holds all 12), and validate with
  `period_error()`. Change the counts only through `LECTURES_PER_DAY` and
  `SATURDAY_LECTURES` (then `makemigrations`: they feed choices and
  constraints).

### Development data
- When a new app has data worth seeing in the UI, add it to
  `base/management/commands/full_seed.py` (and its model to `print_summary`).
  Generate it through the app's services and rules, not hand-computed values,
  and keep it valid for the models' `clean()`.

### Tests
- Add tests in `<app>/tests.py` (Django `TestCase`, `setUpTestData`, test
  client). Tests that hit views use `base.testing.LoggedInTestCase` (its
  `setUp` logs the client in; call `super().setUp()` if you override it).
  Simulate htmx with `**{"HTTP_HX_REQUEST": "true"}` and check
  `assertTemplateUsed` for the partial.

## Known pitfalls

- Every view requires login (`base.middleware.LoginRequiredMiddleware`,
  which answers htmx requests with `HX-Redirect`). Mark public views with
  `@login_not_required`. `/login/` and `/logout/` are Django auth views (URL
  names `login` and `logout`, no namespace); logout is POST-only.
- `manage.py clean` **seeds** reference data despite its name.
