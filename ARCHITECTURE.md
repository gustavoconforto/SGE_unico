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
| `base` | `/` | Abstract models (`TimeStampedModel`, `Person`), htmx search/filter mixins, layout and UI components, users/groups/permissions screens, `clean` seed command |
| `employees` | `/employees/` | `EmployeeRoleType`, `Employee` |
| `programs` | `/programs/` | `Program` (course: Ensino Médio, Pré UNB, Pré ENEM) |
| `classes` | `/classes/` | `Class` (turma) |
| `students` | `/students/` | `Student`, `Guardian`, `GuardianAssociation` |
| `enrollments` | `/enrollments/` | `SchoolYear`, `EnrollmentType`, `DiscountType`, `NeededDocumentType`, `Enrollment`, `EnrollmentNeededDocument` |
| `accounts` | `/accounts/` | `AccountType`, `Supplier`, `Account` (+ receivable/payable proxies), `Installment`, `Payment` |

Dependencies point one way, from the general to the specific:

```
base ◀── employees
base ◀── students ◀── enrollments ──▶ classes ──▶ programs
                          │  ▲
                          ▼  │ (signals)
                       accounts
```

`accounts` imports `Enrollment` and `Guardian`. `enrollments` reaches
`accounts` only through **signals** (`enrollments/signals.py`) and the
installment formset on the enrollment edit page. `classes.Class.year` refers to
`enrollments.SchoolYear` by string to avoid a circular import.

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
| `Installment` | account, `number` (unique per account), `due_date`, `amount`, `status`: `A` open, `P` partially paid, `Q` paid, `C` cancelled |
| `Payment` (baixa) | installment, `paid_at`, `amount` (total received, **including** penalty, interest and monetary adjustment), the three charges, method (PIX, boleto, cash, card, transfer, check) |

**Integrity rules**

- Every financial FK is `on_delete=PROTECT`. Deleting something that's in use
  shows a message instead of an error (`ProtectedDeleteMixin`).
- Principal paid = `amount − penalty − interest − monetary_adjust`.
  `PaymentForm` won't let the principal go over the installment's balance or
  drop to zero or below.
- `Payment.save()` and `delete()` call `Installment.refresh_status()`, which
  sets the status from the principal paid (open → partial → paid). Cancelled
  installments are never changed by it.
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

- `base.html`: loads the CDNs and the Inter font, defines the `.nav-*`
  component classes, and renders flash messages. Blocks: `title`,
  `extra_head`, `page_title` (navbar heading), `header` (above content: action
  buttons and search), `content`, `extra_js`.
- `sidebar.html`: sections **Recursos Humanos**, **Configuração de
  Matrículas**, **Financeiro**, **Acadêmico**. Each entry is
  `<a href={% url "app:name" %} class="nav-link"><svg …/>Label</a>`, with a
  24×24 outline Heroicons icon at `stroke-width="1.5"`. Collapsible on desktop,
  off-canvas on mobile (`sidebar_js.html`).

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
  open = `badge-neutral badge-outline`. Overdue rows get `bg-red-50` and a red
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

## Testing

Django's `TestCase` with the test client. `accounts/tests.py` covers views,
forms, filters, htmx partials and protected deletes; `enrollments/tests.py`
covers the installments generated for an enrollment and the settings
redirects. The other apps have no tests yet. htmx requests
are simulated with `HTTP_HX_REQUEST="true"`. New features should come with
tests in the same style.

## Known issues and technical debt

- **No authentication or authorization** on app views. Users, groups and
  permissions can be managed, but nothing checks them.
- **Production settings are missing:** `DATABASES` is empty without debug,
  `ALLOWED_HOSTS = []`, CDN assets aren't pinned/self-hosted.
- `Enrollment.installments_count` exists (default 12) but isn't used:
  the number of installments comes from the enrollment date (see
  [workflow](#enrollment--finance-workflow)).
- `reset_db.py` option 2 calls a missing `seed` command. The seed logic lives
  in `base/management/commands/clean.py`, whose name suggests the opposite.
- `enrollments/forms.py` and `accounts/forms.py` each define an
  `InstallmentForm` with different purposes.
- `pandas` is an unused dependency. `tailwind.config.js` and `src/gestao/`
  (uv scaffolding) are empty or unused.
- `Account.balance()` and `Installment.balance()` query per object. Prefer the
  `with_balance()` annotation in lists.
