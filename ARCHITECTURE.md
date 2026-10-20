# Architecture

How Gestão Escolar is put together: the apps, the data model, how a request is
handled, the financial rules, and the UI conventions. For setup, see
[README.md](README.md).

## Overview

A single Django project (`config/`) with one app per business area. Pages are
rendered on the server with Django templates. Interactivity is done with
**htmx** (live search, filters, pagination) instead of a JavaScript framework.
Styling is **Tailwind CSS 4** plus **daisyUI 5**, both loaded from a CDN in
`base/templates/base/base.html`, so there's no front-end build step.

```
Browser ──HTTP──▶ config/urls.py ──▶ <app>/urls.py ──▶ class-based view
                                                        │
                    full page  ◀── template ◀───────────┤ (normal request)
                    fragment   ◀── partial  ◀───────────┘ (htmx request)
```

## Apps and dependencies

| App | URL prefix | Responsibility |
|---|---|---|
| `base` | `/` | Abstract models (`TimeStampedModel`, `Person`), htmx search/filter mixins, layout and UI components, login page template, users/groups/permissions screens, `clean` and `seed` commands |
| `employees` | `/employees/` | `EmployeeRoleType`, `Employee` |
| `programs` | `/programs/` | `Program` (course: Ensino Médio, Pré UNB, Pré ENEM) |
| `classes` | `/classes/` | `Class` (turma), and the class roster page (students actively enrolled in a class) |
| `grades` | `/grades/` | `Subject` (matéria). Grade entry (notas) is planned here but not built |
| `students` | `/students/` | `Student`, `Guardian`, `GuardianAssociation` |
| `enrollments` | `/enrollments/` | `SchoolYear`, `EnrollmentType`, `DiscountType`, `NeededDocumentType`, `Enrollment`, `EnrollmentNeededDocument` |
| `accounts` | `/accounts/` | `AccountType`, `Supplier`, `Account` (+ receivable/payable proxies), `Installment`, `Payment` |
| `billing` | `/billing/` | Bradesco CNAB 400 bank slips: `BankSettings`, `Remittance` (.REM), `BankSlip`, `ReturnFile` (.RET), `ReturnEvent` |

Dependencies point one way, from the general to the specific:

```
base ◀── employees
base ◀── students ◀── enrollments ──▶ classes ──▶ programs
                          │  ▲
                          ▼  │ (signals)
                       accounts ◀── billing

grades (standalone for now)
```

`accounts` imports `Enrollment` and `Guardian`. `enrollments` reaches
`accounts` only through **signals** (`enrollments/signals.py`) and the
installment formset on the enrollment edit page. `classes.Class.year` refers to
`enrollments.SchoolYear` by string to avoid a circular import. The one
exception to the arrow is `classes/views.py`, which imports `SchoolYear`,
`EnrollmentStatus` and `Student` for the class roster page. Keep those imports
in views; `classes/models.py` must not import `enrollments` or `students`.

## Data model

### Shared abstract models (`base/models.py`)

- **`TimeStampedModel`**: `created_at`, `updated_at`.
- **`Person(TimeStampedModel)`**: name, sex, CPF and RG (both unique), issuing
  authority, birth date, nationality, place of birth, phone, mobile, email,
  and address (street, neighborhood, city, UF, CEP). Used by `Employee`,
  `Student` and `Guardian`. Documents are stored **digits only**.

### Entity relationships

```mermaid
erDiagram
    Program ||--o{ Class : has
    SchoolYear ||--o{ Class : has
    Program ||--o{ EnrollmentType : priced_by
    SchoolYear ||--o{ EnrollmentType : priced_by
    Student ||--o{ GuardianAssociation : ""
    Guardian ||--o{ GuardianAssociation : ""
    Student ||--o{ Enrollment : ""
    EnrollmentType ||--o{ Enrollment : ""
    Class |o--o{ Enrollment : ""
    DiscountType |o--o{ Enrollment : ""
    Enrollment ||--o{ EnrollmentNeededDocument : ""
    NeededDocumentType ||--o{ EnrollmentNeededDocument : ""
    Enrollment |o--o| Account : "contract account"
    Guardian |o--o{ Account : "pays (receivable)"
    Supplier |o--o{ Account : "is paid (payable)"
    AccountType ||--o{ Account : categorizes
    Account ||--o{ Installment : ""
    Installment ||--o{ Payment : ""
    EmployeeRoleType ||--o{ Employee : ""
```

### Academic models

| Model | Key fields and rules |
|---|---|
| `Program` | `name` unique |
| `SchoolYear` | start/end dates plus start/end of each of the 4 bimesters; `__str__` is the year |
| `Class` | program, school year, optional grade level (1–3), name, shift (`M/T/N/I`), capacity. Unique per (year, program, name) |
| `Student(Person)` | `registration` auto-generated as `<year><5-digit sequence>` (e.g. `202600001`); social name; photo saved as `media/students/<registration>.<ext>`, with the old file removed on change and a placeholder when missing |
| `Guardian(Person)` | marital status |
| `GuardianAssociation` | student ↔ guardian with relationship and flags: `is_financial`, `is_primary_contact`, `living_with`, `pick_up`. Unique per pair |
| `EnrollmentType` | contract template: program, level, school year, `total_price`. Contract dates default to the school year's |
| `DiscountType` | description and percentage (0–100) |
| `Enrollment` | student, contract type, optional class, status (`A` active, `T` transferred, `D` dropped, `C` completed, `X` cancelled), date, discount, `due_day` (1–28). Copies `gross_value` and `discount_percent` from the contract and discount on save, so later price changes don't affect existing contracts. Unique per (student, contract type) |
| `EnrollmentNeededDocument` | one row per required document type per enrollment, with `is_delivered` |
| `Subject` (`grades`) | `name` unique. Not linked to classes or programs yet. `seed` creates the ten high-school subjects |

`Enrollment.clean()` requires the student to have a **financial guardian**, and
the class to match the contract's year, program and grade.

### Financial models (`accounts/models.py`)

Money is always `DecimalField(max_digits=10, decimal_places=2)` (the `MONEY`
constant). Never use floats.

| Model | Key fields and rules |
|---|---|
| `AccountType` | financial category, with `direction` `R` (receivable) or `P` (payable). Name unique |
| `Supplier` | name, CPF/CNPJ (digits, unique when filled), contacts |
| `Account` | `direction`, description, category, issue date, `gross_value`, `discount_value`, notes. Counterpart: `guardian` and/or `enrollment` for receivables, `supplier` for payables, enforced by a DB check constraint. `net_value = gross − discount` |
| `AccountReceivable`, `AccountPayable` | **proxy models** of `Account`, each with a manager filtered by direction and a `save()` that sets it. Views and forms use these |
| `Installment` | account, `number` (unique per account), `due_date`, `amount`, `status`: `A` open, `P` partially paid, `Q` paid, `C` cancelled, `E` expired (bank wrote off the unpaid slip; still owed). `PENDING_STATUSES` = open, partial, expired |
| `Payment` (baixa) | installment, `paid_at`, `amount` (total received, **including** penalty, interest and monetary adjustment), the three charges, `discount` (e.g. punctuality; settles principal without being received), method (PIX, boleto, cash, card, transfer, check) |

**Integrity rules**

- Every financial FK is `on_delete=PROTECT`. Deleting something that's in use
  shows a message instead of an error (`ProtectedDeleteMixin`).
- Principal paid = `amount − penalty − interest − monetary_adjust + discount`.
  `PaymentForm` won't let the principal go over the installment's balance or
  drop to zero or below.
- `Payment.save()` and `delete()` call `Installment.refresh_status()`, which
  sets the status from the principal paid (open → partial → paid). Cancelled
  installments are never changed by it; expired ones only move to paid.
- An account's `gross_value` and `discount_value` are locked after creation,
  because they were already split into installments.
- A category's `direction` is locked once accounts use it.
- An account with payments can't be deleted. Without payments, its
  installments are deleted with it.

**Query helpers**

- `Account.objects.with_installment_summary()` annotates installment counts
  (total, pending, overdue, paid) used by `Account.situation` and the status
  filter, without N+1 queries.
- `Installment.objects.with_balance()` annotates `outstanding` in SQL (same
  rule as `Installment.balance()`), via a subquery so it can be summed.
  Also `.pending()` and `.overdue()`.
- "Overdue" depends on today's date, so it's always computed per request,
  never stored.

## Enrollment → finance workflow

Implemented in `enrollments/signals.py` and `accounts/services.py`.

1. **Enrollment created** (`post_save`, `created=True`):
   - `create_enrollment_account()` creates an `AccountReceivable` in category
     "Mensalidade" (created if missing), linked to the enrollment and the
     student's first financial guardian, using the contract's values.
   - It generates monthly installments, with due dates from
     `enrollment_due_dates()`. The first is due on the enrollment date. The
     rest fall on `due_day` of the **school year**, moved to Monday when that
     day is a weekend (`utils.format.weekdays.adjust_weekend`):
     - enrolling during the school year: one per remaining month, through
       December (enrolled in September → Sep, Oct, Nov, Dec);
     - enrolling ahead (e.g. November 2026 for 2027): 12 installments, the
       first on the enrollment date, then February to December 2027.
   - The net value is split with `split_value()`: every installment gets the
     value rounded down to the cent, and the first gets the remainder, so
     installments always add up to the account's net value.
   - `sync_documents()` creates one `EnrollmentNeededDocument` per required
     document type.
2. **Enrollment changed to transferred, dropped or cancelled**:
   `cancel_future_installments()` cancels the account's **open** installments
   due today or later. Partially paid ones are kept.
3. The **enrollment edit page** shows the documents checklist and the
   installments as inline formsets, saved in one transaction.

Accounts created by hand use `build_installments()` instead: the net value is
split into N monthly installments starting on the chosen first due date, with
the same `split_value()` rounding.

## Bank slips (`billing`)

Bradesco "Cobrança" in CNAB 400. `billing/cnab400.py` is pure Python (no
Django): it writes remittance files and parses return files. Its fixed values
match files the bank already accepted (`00000 000000000000 ` in positions
2–20, `N` in 94, `2` in 106, CRLF line endings, no EOF byte).
`billing/services.py` holds the workflow:

1. **Settings** (`BankSettings`, single row edited at `settings/edit/`):
   company code, wallet, agency/account, fine % (2), monthly interest % (1),
   and the last remittance number.
2. **Remittance** (`create_remittance`): one `.REM` carries new slips
   (movement `01`) and write-off requests (movement `02`). Candidates for new
   slips are receivable installments with status in `PENDING_STATUSES`, a
   balance, and no *live* slip (generated, registered or write-off
   requested). Installments whose financial guardian lacks a
   valid CPF, address or CEP, or whose due date has passed, are listed but
   skipped. Each slip gets nosso número `2000` + slip id (11 digits) plus its
   check digit; participant control = slip id; document number =
   installment id. The amount is the outstanding balance; daily interest =
   amount × monthly % / 30; the punctuality discount comes from
   `EnrollmentType.punctuality_discount` (only for enrollment accounts, valid
   until the due date). The file is stored in `Remittance.content` and
   downloaded as `<number:08>.REM`. A remittance the bank hasn't processed
   (new slips still "generated", write-offs still "requested") can be
   deleted: its write-offs go back to "registered", and the number is freed
   if it was the last.
3. **Write-off request** (pedido de baixa): `write_off_candidates()` lists
   registered slips whose installment was cancelled or paid another way
   (balance below the slip amount, e.g. paid in cash). Selected slips are
   sent again with movement `02` and become "write-off requested", which is
   still live: the installment gets a new slip only after the bank confirms
   with `10`. A partially paid installment is then resent for its balance.
4. **Return** (`import_return`): rejects other company codes and files already
   imported (sha256); lines already seen (fingerprint) are skipped. Slips are
   matched by nosso número; lines from the previous system (another prefix)
   are stored as *ignored*. Per occurrence code:
   - `02` slip registered; `03` slip rejected (installment can be resent);
   - `06`/`15`/`17` creates a `Payment` (method boleto) with the bank's
     interest and discount, so principal = paid − interest + discount. A
     principal above the balance, a cancelled installment or a slip already
     settled is flagged as an *error* for manual handling;
   - `22`/`40` deletes that payment (installment reopens), slip reversed;
   - `09` slip expired and the installment set to **expired**;
   - `10` slip written off, confirming a write-off request (a message is left
     if the installment still has a balance, so it can be resent);
   - `27` write-off rejected: the slip goes back to registered;
   - other codes are stored as *ignored*.
   Each line runs in a savepoint, so one bad line doesn't stop the file.

## Request handling

### Views

Views are **class-based** (`ListView`, `CreateView`, `UpdateView`,
`DeleteView`). The exceptions still written as functions are
`base/views.py` (users, groups, permissions) and the student add/edit views
(form plus guardian formset with tabs).

URLs follow one pattern per resource:

```
<resource>/list/   <resource>/add/   <resource>/edit/<pk>/   <resource>/delete/<pk>/
name: <resource>_list, _add, _edit, _delete     namespace: the app's app_name
```

### Authentication

`config/urls.py` maps `/login/` to Django's `LoginView` (template
`base/templates/login/login.html`, `redirect_authenticated_user=True`) and
`/logout/` to `LogoutView`, which only accepts POST. These URL names (`login`,
`logout`) have no namespace. Settings: `LOGIN_URL = "login"`,
`LOGIN_REDIRECT_URL = "base:main"`, `LOGOUT_REDIRECT_URL = "login"`.

The login page is standalone: it doesn't extend `base/base.html`. No app view
requires login yet (no `LoginRequiredMixin` or middleware), and the UI has no
logout button.

### Search, filters and htmx (`base/search.py`)

- **`HtmxSearchMixin`**: filters by `?q=` using `icontains` over
  `search_fields` (OR between fields). When the request comes from htmx
  (`HX-Request`, and isn't a history restore), it renders
  `partial_template_name` instead of the full page.
- **`HtmxFilterMixin(HtmxSearchMixin)`**: also binds `filter_form_class` to
  `request.GET`. Each non-empty value is applied as
  `filter_lookups.get(name, name)=value`, or by calling `filter_<name>(qs, value)`
  on the view when the filter needs custom logic.

List pages are built in three parts:

```
<thing>_list.html                      full page: header + filter_form + #search-results
└── partials/<thing>_table.html        table + pagination (the only part htmx swaps)
components/search/filter_form.html     hx-get on input (500 ms debounce),
                                       hx-target="#search-results", hx-push-url
```

Pagination links also use `hx-get`, so search, filters and the page number all
stay in the URL and survive reloads and the back button.

### Dependent selects (class roster, `classes/detail/`)

`ClassDetailView` (`HtmxSearchMixin` + `ListView` of `Student`) lists students
with an **active** enrollment in `?school_class=<pk>`. With no class selected
it returns an empty queryset. The page has two selects:

```
school_year select ──hx-get──▶ ClassOptionsView (classes/detail/class-options/)
                               returns partials/class_select.html:
                               • the class select, filtered by year (outerHTML swap of #class-select)
                               • an empty #search-results with hx-swap-oob, clearing the old table
                               • HX-Push-Url: classes/detail/?school_year=<pk>
school_class select ──hx-get──▶ ClassDetailView (hx-include the year, hx-push-url)
                               returns partials/class_detail_table.html into #search-results
```

Both values stay in the URL, so a reload rebuilds the page from
`?school_year=&school_class=`. `get_int_param()` ignores non-numeric values.
Use this pattern for any "pick A, then B filtered by A" screen. The page has no
sidebar link yet.

### Mixin order

Mixins go left of the generic view. A mixin whose `get_queryset()` adds
annotations used by filters must be to the **right** of `HtmxFilterMixin`, so
its annotations exist before filtering. Example: `InstallmentSummaryMixin` in
`AccountListMixin`.

### Receivable / payable views

Both share templates. Each concrete view only declares its proxy model, form,
`url_prefix` and labels. `AccountContextMixin` passes `title`, `subtitle_*`,
`counterpart_label` and a `urls` dict to the templates (e.g.
`{% url urls.edit account.pk %}`).

## Design system

The look is set by Tailwind utilities and a few daisyUI classes. Match existing
pages; don't introduce new colors or components without a reason.

### Layout (`base/templates/base/`)

- `base.html`: loads the CDNs, the Inter font and the Material Symbols
  Outlined icon font (Google Fonts), defines the `.nav-*` component classes,
  and renders flash messages. It includes `sidebar/sidebar.html`,
  `navbar/navbar.html` and `sidebar/js/sidebar_js.html`. Blocks: `title`,
  `extra_head`, `page_title` (navbar heading), `header` (above content: action
  buttons and search), `content`, `extra_js`.
- `sidebar/sidebar.html`: sections **Recursos Humanos**, **Configuração de
  Matrículas**, **Financeiro**, **Acadêmico**, each a daisyUI `menu` with a
  `<details>` toggle. Collapsible on desktop, off-canvas on mobile
  (`sidebar/js/sidebar_js.html`). The sections are being moved to components:
  - **Recursos Humanos** is in `sidebar/menu/recursos_humanos/menu.html`, and
    each entry is
    `{% include 'base/sidebar/items/menu_item.html' with path="app:name" label="…" icon="…" %}`,
    where `icon` is a [Material Symbols](https://fonts.google.com/icons) name.
  - The other sections are still inline in `sidebar/sidebar.html`. Each entry
    is `<a href={% url "app:name" %} class="nav-link"><svg …/>Label</a>`,
    with a 24×24 outline Heroicons icon at `stroke-width="1.5"`.
  - **Acadêmico** has a nested **Edição** submenu (Turmas, Matérias, Notas)
    above Matrículas, Alunos and Responsáveis.

  Add a new entry in the style of its section. `base/templates/base/sidebar.html`
  (no subfolder) is the old copy and is no longer included anywhere.

### Page patterns

| Page | Structure |
|---|---|
| List | `header`: right-aligned "Adicionar registro" button + `filter_form.html` with a `placeholder` naming the searchable fields. `content`: `<div id="search-results">{% include partial %}</div>` |
| Add / edit | centered `h2` "Gerenciamento de <plural lowercase>" + subtitle, then `<thing>_form.html` in a `bg-slate-50 rounded-2xl p-6 md:p-8` card. Fields side by side go in `flex w-full gap-4` rows |
| Delete | same header, subtitle "Deseja, realmente, deletar este registro?", one `<p>` per key field, red delete button + cancel |

### Components (`base/templates/components/`)

| Component | Use |
|---|---|
| `form/field.html` | label, widget, help text, errors. Use for every form field |
| `form/checkbox.html` | inline label + checkbox |
| `button/button_submit_form.html` | primary action (slate-700) |
| `button/button_delete_form.html` | destructive submit (red-700) |
| `button/button_select.html` | secondary/outline button, wrapped in `<a>` for links (Editar, Deletar, Baixar…) |
| `button/button_cancel.html` | cancel, wrapped in `<a>` back to the list |
| `search/filter_form.html` | search input + the view's `filter_form` grid + "Limpar filtros" |
| `table/pagination.html` | htmx pagination (uses `{% querystring %}`) |
| `table/empty_table.html` | "Nenhum registro encontrado" row; pass `collspan` (sic) |

### Visual rules

- **Palette:** neutral slate/gray. Red is for the brand and destructive actions,
  green/lime for success and receivables.
- **Tables:** `rounded-xl border border-slate-200 bg-white shadow-sm`, header
  `bg-slate-50 text-xs uppercase tracking-wide text-slate-600`, rows
  `hover:bg-slate-50`, right-aligned "Opções" column last. Money and numbers
  are right-aligned and `whitespace-nowrap`.
- **Badges** (daisyUI `badge badge-sm`): receivable = `badge-success
  badge-outline`, payable = `badge-error badge-outline`; installment status
  paid = `badge-success`, partial = `badge-warning`, cancelled = `badge-ghost`,
  expired = `badge-error`, open = `badge-neutral badge-outline`. Overdue rows get `bg-red-50` and a red
  "Vencida" label.
- **Form widgets** (set in the form's `widgets`): `input input-neutral w-full`,
  `select select-neutral w-full`, `textarea textarea-neutral w-full`; add
  `-sm` / `select-sm` in filter forms. Dates use `date_input()` in
  `accounts/forms.py` (`type="date"`, ISO format).
- **Formatting:** dates `|date:"d/m/Y"`; money `R$ {{ value|floatformat:2 }}`;
  ordinals `{{ n }}ª`.
- **Flash messages** after every create/update/delete:
  "Registro cadastrado com sucesso" (success), "Registro atualizado com
  sucesso" (success), "Registro deletado com sucesso" (warning), errors as
  `messages.error`.

## Configuration

- `config/settings.py` reads `SECRET_KEY` and `DJANGO_DEBUG` from `.env`
  (python-dotenv).
- Locale `pt-br`, timezone `America/Sao_Paulo`, `USE_TZ=True`. Accepted date
  input formats include `dd/mm/yyyy` and ISO.
- Static: `assets/` → `/static/`. Media: `media/` → `/media/`, served by Django
  only in debug.
- Message levels are mapped to `alert-*` tags, which `base.html` turns into
  colors.
- Login redirects: see [Authentication](#authentication).
- Linting: `ruff` is a project dependency, with no custom configuration. The
  existing code isn't clean yet (lint errors, unformatted files), so run it on
  the files you change.

## Testing

Django's `TestCase` with the test client. `accounts/tests.py` covers views,
forms, filters, htmx partials and protected deletes. `billing/tests.py` covers
CNAB files, remittances, write-offs and return import. `enrollments/tests.py`
covers the installments generated for an enrollment and the settings
redirects. `base/tests.py` covers the login page, and `classes/tests.py` the
class roster page and its year → class select. `employees`, `programs`,
`students` and `grades` have no tests yet. htmx requests are simulated with
`HTTP_HX_REQUEST="true"`. New features should come with tests in the same
style.

## Known issues and technical debt

- **No authorization, and login isn't enforced.** The login page works, but
  every app view is public. Users, groups and permissions can be managed, but
  nothing checks them. There's no logout button.
- **Production settings are missing:** `DATABASES` is empty without debug,
  `ALLOWED_HOSTS = []`, CDN assets aren't pinned/self-hosted.
- `Enrollment.installments_count` exists (default 12) but isn't used:
  the number of installments comes from the enrollment date (see
  [workflow](#enrollment--finance-workflow)).
- `enrollments/forms.py` and `accounts/forms.py` each define an
  `InstallmentForm` with different purposes.
- `tailwind.config.js` and `src/gestao/` (uv scaffolding) are empty or unused.
- The `grades` subject CRUD doesn't use `SuccessMessageMixin` or
  `ProtectedDeleteMixin` yet, so it shows no flash messages.
- `Account.balance()` and `Installment.balance()` query per object. Prefer the
  `with_balance()` annotation in lists.
