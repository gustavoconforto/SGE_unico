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
| `base` | `/` | Abstract models (`TimeStampedModel`, `Person`), htmx search/filter mixins, layout and UI components, login page template, `LoginRequiredMiddleware`, users/groups/permissions screens, `clean`, `seed` and `full_seed` commands |
| `employees` | `/employees/` | `EmployeeRoleType`, `Employee` |
| `programs` | `/programs/` | `Program` (course: Ensino Médio, Pré UNB, Pré ENEM) |
| `classes` | `/classes/` | `Class` (turma), and the class page (the class's subjects and the students actively enrolled in it) |
| `departments` | `/departments/` | `Department`: groups subjects and the teachers who can teach them |
| `grades` | `/grades/` | `Subject` (matéria), `ExamType`, `GradeLevelSubject`, `Grade`; grade entry sheet, report card, grade calculation (`grades/services.py`) |
| `students` | `/students/` | `Student`, `Guardian`, `GuardianAssociation` |
| `enrollments` | `/enrollments/` | `SchoolYear`, `EnrollmentType`, `DiscountType`, `NeededDocumentType`, `Enrollment`, `EnrollmentNeededDocument` |
| `accounts` | `/accounts/` | `AccountType`, `Supplier`, `Account` (+ receivable/payable proxies), `Installment`, `Payment` |
| `incidents` | `/incidents/` | Student conduct records, all per enrollment: `IncidentType` (with a penalty), `Incident`, `StudentDelay` (atraso), `BathroomPermission` (saída para banheiro) |
| `q_and_a` | `/q_and_a/` | `QandA` (plantão de dúvidas): a student's attendance at a subject's Q&A session, per enrollment |
| `pathways` | `/pathways/` | Extra-curricular pathways (itinerários): `Pathway`, `PathwayOffering`, `PathwayEnrollment`, `PathwaySession`, `PathwayAttendance`, `PathwayGrade`, and `ExtraGradeSettings`; the extra grade calculation (`pathways/services.py`) |
| `lessons` | `/lessons/` | Weekly timetable (grade horária) and class diary (diário de classe): `TimetableSlot`, `Lecture` |
| `billing` | `/billing/` | Bradesco CNAB 400 bank slips: `BankSettings`, `Remittance` (.REM), `BankSlip`, `ReturnFile` (.RET), `ReturnEvent` |

Dependencies point one way, from the general to the specific:

```
base ◀── employees
base ◀── students ◀── enrollments ──▶ classes ──▶ programs
                          │  ▲
                          ▼  │ (signals)
                       accounts ◀── billing

employees ◀── departments ◀── grades ──▶ enrollments, classes, employees
                                incidents ──▶ enrollments
                                  q_and_a ──▶ enrollments, grades, incidents (forms)
                                 pathways ──▶ enrollments, employees, grades, incidents, q_and_a (services)
                                  lessons ──▶ classes, grades, employees, departments (via grades)
```

`accounts` imports `Enrollment` and `Guardian`. `enrollments` reaches
`accounts` only through **signals** (`enrollments/signals.py`) and the
installment formset on the enrollment edit page. `classes.Class.year` refers to
`enrollments.SchoolYear` by string to avoid a circular import. The one
exception to the arrow is `classes/views.py`, which imports `SchoolYear`,
`EnrollmentStatus` and `Student` for the class roster page. Keep those imports
in views; `classes/models.py` must not import `enrollments` or `students`.
`classes/views.py` also imports `grades.models.GradeLevelSubject` to list the
subjects of the selected class's series on the class page.

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
| `Department` (`departments`) | `name` unique; `teachers` (many-to-many to `Employee`; a teacher can be in several departments). Can't be deleted while subjects use it |
| `Subject` (`grades`) | `name` unique; optional `department`. `seed` creates the ten high-school subjects |

### Grade models (`grades/models.py`)

| Model | Key fields and rules |
|---|---|
| `ExamType` | name and `code` (both unique, code upper-cased by the form), `kind` (`R` avaliação, `B` ponto extra, `C` recuperação), `max_score` (> 0), `order` (column order). There are no weights: each exam's `max_score` is its share of the bimester (e.g. PS 3, PB 6, comportamento 1) |
| `GradeLevelSubject` | a subject taught in every class of a series (`grade_level` 1–3, matched against `Class.grade_level`), with **several teachers** (`teachers`, many-to-many to `Employee`, limited to the teachers of the subject's department) and classes per week (decimal, ≥ 0: a weekly mean such as 1,5). Unique per (series, subject). The report card's rows and the grade entry subjects come from it; a class without a series has no subjects |
| `Grade` | **enrollment** (not student: it fixes year and class), subject, exam type, bimester (1–4), `score` (0 to the exam's `max_score`). Unique per (enrollment, subject, exam type, bimester). `clean()` requires the subject to be taught in the series of the enrollment's class |

Grades and averages are never stored; `grades/services.py` computes them per
request:

- `bimester_grade(grades)`: **sum** of the `R` and `B` scores, capped at 10
  (so extra points can't go past 10). `C` scores don't count. `None` without
  any `R` score. Rounded half-up to cents.
- `final_average(grades)`: the **annual average**, the weighted mean of the four
  bimester grades (20%, 30%, 20%, 30%) rounded to the half point (.25 → .5,
  .75 → next whole), `None` until all four exist. `PASSING_GRADE` is 6.00.
- **Final recovery**: a student whose annual average is below 6 takes the
  recovery exam (`C`) of that subject. Its grades are stored with
  `bimester = FINAL_RECOVERY` (5, "Recuperação final"); `Grade.clean()` keeps
  `C` exams in that period and every other exam out of it. `final_grade(average,
  recovery)` is the mean of the average and the recovery score, rounded to the
  half point; the student passes when it is ≥ 6. A recovery score is ignored
  when the average is already ≥ 6.
- `report_card(enrollment)`: one `ReportCardRow` per subject of the class's series (4 bimester grades,
  `average`, `recovery`, `final`, `passed`), in two queries. `passed` is `None`
  while the year is incomplete or the recovery score is missing ("Em recuperação").

`Enrollment.clean()` requires the student to have a **financial guardian**, and
the class to match the contract's year, program and grade.

### Incident models (`incidents/models.py`)

Conduct records point at an **enrollment**, not a student, for the same reason
as `Grade`: the enrollment fixes the school year and the class
(`enrollment.school_class`). Each has an `incident_date` (the day it
happened, which can differ from `created_at`).

| Model | Key fields and rules |
|---|---|
| `IncidentType` | `type` unique, `penalty` (decimal, ≥ 0, `CheckConstraint`) |
| `Incident` | enrollment (`related_name="incidents"`), incident type, `incident_date` |
| `StudentDelay` | enrollment (`delays`), `delay_type` (`A` tolerado, `U` não tolerado), `incident_date` |
| `BathroomPermission` | enrollment (`bathroom_permissions`), `class_period` (the lesson, ≥ 1, checked by the form), `incident_date` |

The forms share `ActiveEnrollmentFormMixin` (`incidents/forms.py`): the
enrollment select lists only active enrollments, plus the record's current one
when editing. The lists search by student name and show the class.

### Q&A session model (`q_and_a/models.py`)

`QandA` (plantão) records that a student attended a subject's Q&A session:
enrollment (`related_name="q_and_as"`), subject (`grades.Subject`,
`related_name="q_and_as"`) and `q_and_a_date`. Like the incident models it
points at an enrollment and its form reuses `ActiveEnrollmentFormMixin`. The
list searches by student or subject name and filters by subject and date range
(`QandAFilterForm`).

### Pathway models (`pathways/models.py`)

Extra-curricular courses. A student picks pathways every year, with no
contract or installments; what they earn is extra points in the bimester.

| Model | Key fields and rules |
|---|---|
| `Pathway` | catalog: `name` unique, `description`, `extra_points` (≥ 0, the most it adds in a bimester) |
| `PathwayOffering` | a pathway running in a `SchoolYear`: optional `name` (to tell groups apart), `teachers` (many-to-many to `Employee`), optional `capacity`, `schedule` (free text). Unique per (pathway, year, name) |
| `PathwayEnrollment` | **enrollment** × offering, `joined_at`, `left_at` (leaving sets it instead of deleting). Unique per pair. `clean()` requires the offering to be in the enrollment's school year and a free seat (members without `left_at`) |
| `PathwaySession` | a lesson (aula): offering, `date` inside the school year, optional `topic` |
| `PathwayAttendance` | session × pathway enrollment, `status` (`P` presente, `F` falta, `J` falta justificada). Deleted with its session. `clean()` requires the same offering and membership on the lesson's date |
| `PathwayGrade` | the pathway teacher's score per pathway enrollment and bimester (1–4), 0–10. Unique per (pathway enrollment, bimester) |
| `ExtraGradeSettings` | per `SchoolYear` (one-to-one), created with the defaults by `for_school_year()`: `min_pathway_attendance` (75%), `q_and_a_min_sessions` (3), `q_and_a_points` (0.50). Edited at `pathways/extra_grade_settings/` |

**Extra grade** (`pathways/services.py`, like the concept grade): for each
enrollment and bimester, every pathway adds `score / 10 × extra_points` when
attendance (`P / (P + F)`, `J` left out) over the bimester's lessons reaches
`min_pathway_attendance`; no lessons, no grade or low attendance add 0. Q&A
sessions add `q_and_a_points` with at least `q_and_a_min_sessions` in the
bimester (`q_and_a/services.py`). The sum is capped at the max score of the
`EX` exam type and `save_extra_grades()` writes it, zero included, to every
subject of the series through `grades.services.save_series_grades()` (shared
with `save_concept_grades()`). `EX` is therefore calculated, not typed. Settings
changes only affect later calculations.

**Screens** (sidebar section "Itinerários", `base/sidebar/menu/itinerarios.html`):
standard CRUDs for pathways (`pathways/`), offerings (`pathways/offerings/`,
filter by year and pathway, with links to the offering's roster, lessons and
grades) and the roster (`pathways/enrollments/`, filter by offering and
situation). Roster and lessons take `?offering=<pk>` to prefill the form and
return to the filtered list; with the offering known, the enrollment select
lists only that year's active enrollments. Leaving is recorded with `left_at`;
deleting a member with attendance or grades is blocked.

- **Lessons** (`pathways/sessions/`): "Nova aula" saves the lesson and opens
  its roll call (`sessions/attendance/<pk>/`, `AttendanceSheetForm`): one status
  per student in the pathway on that date, present by default. A lesson's
  offering can't be changed; moving its date removes the attendance of students
  who weren't in the pathway then. The list shows present and absent counts,
  or "Sem chamada".
- **Pathway grades** (`pathways/grades/entry/`): pick offering and bimester;
  `PathwayGradeSheetForm` has one optional 0–10 score per student in the pathway
  during the bimester (blank deletes), and shows each one's attendance and the
  extra points the saved score gives.
- **Extra grade** (`pathways/extra_grades/all/` and `individual/`): the concept
  grade screens (`IncidentGradesAll` / `IncidentGradesIndividual`), subclassed
  through their `get_exam_type()`, `save_grades()`, `exam_type_missing` and
  `url_name` hooks.
- **Rules** (`pathways/extra_grade_settings/`): one row per school year.

### Lesson models (`lessons/models.py`)

The regular lessons of a class: 7 periods a day, Monday to Friday. Only
classes with a series (`grade_level`) have them, since only they have subjects.

| Model | Key fields and rules |
|---|---|
| `TimetableSlot` | class, `weekday` (1–5, `Weekday`), `period` (1–7, `PERIODS`), `subject` (`GradeLevelSubject`), `teacher`. Unique per (class, weekday, period). One timetable per class, valid for its year; editing it never changes saved lectures. `clean()` requires the subject in the class's series, the teacher among the subject's `teachers`, and no other class of the same year **and shift** with that teacher in that weekday and period |
| `Lecture` | class, `date`, `period`, `subject`, `teacher`, `topic` (required). Unique per (class, date, period). Subject and teacher are copied from the timetable, so a substitution only changes the lecture. `clean()` requires a weekday inside the class's school year (`lecture_date_error()`), the subject in the class's series and a teacher from `lecture_teachers()`: the subject's teachers or any teacher of its department |

Days without lectures (holidays, events) simply have no rows: there's no
calendar. `lessons/services.py` builds the timetable grid and `weekly_load()`,
the periods scheduled per subject against `GradeLevelSubject.weekly_classes`
(a weekly mean, so a mismatch is only a warning).

**Screens** (sidebar section "Acadêmico"):

- **Timetable** (`lessons/timetable/?school_class=<pk>`): the 5 × 7 grid and
  the weekly load. `timetable/edit/<pk>/` (`TimetableForm`) has one
  "Matéria — Professor" select per cell, built from the series' subjects ×
  their teachers; a blank cell deletes the slot. The whole grid is validated
  before anything is saved.
- **Day sheet** (`lessons/lectures/day/?school_class=<pk>&date=<iso>`,
  `LectureDayForm`): a row per period, prefilled from the saved lecture or the
  timetable. Rows with a topic are saved, clearing a topic deletes the lecture,
  and one invalid row saves nothing. This is the only way to add lectures.
- **Class diary** (`lessons/lectures/list/`): filters by year, class, subject,
  teacher and date range; search by topic. Edit and delete one lecture.

Attendance per lecture is not built yet; it would be a
`LectureAttendance(lecture, enrollment, status)` deleted with its lecture.

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

## Development data (`base/management/commands/`)

- `clean` seeds reference data (users, programs, school years, classes…)
  despite its name; `seed` adds a few fake people.
- `full_seed` **flushes the database** and fills a whole school year sized to
  stress the UI (31 classes × 45 students by default; `--students-per-class`,
  `--year`, `--today`, `--random-seed`). It goes through the app's own rules:
  enrollments are saved one by one so the signal builds their accounts, bank
  slips go through `billing/services.py`, and the concept and extra (`EX`)
  grades come from `concept_grades()` and `extra_grades()` over the seeded
  incidents, Q&A sessions and pathways. Teachers per subject are sized so
  nobody gives more than 25 periods a week; each class's teacher of a subject
  is fixed, and the timetables are built with no teacher clash in a shift.
  The class diary copies the timetable on every school day up to `--today`
  (national holidays and the breaks between bimesters left out), with a few
  substitutes and missing days. Extend it when a new app has data worth
  seeing in the UI.

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

The login page is standalone: it doesn't extend `base/base.html`. Every other
view requires login through `base.middleware.LoginRequiredMiddleware` (Django's,
answering htmx requests with `HX-Redirect` instead of a 302); public views are
marked `@login_not_required`. The logout button (a POST form) is in the user
menu at the bottom of the sidebar.

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
sidebar link yet. When a class is picked, the partial also shows the subjects
and teachers of the class's series (read-only), linking to the "Matérias por
série" list (`grades:grade_level_subject_list?grade_level=<n>`), a standard
CRUD with a series filter where subjects and teachers are managed. In its
form, `GradeLevelSubjectForm` limits the teacher checkboxes to the subject's
department (none, with a help text, when the subject has no department);
changing the subject reloads them from `grades:grade_level_subject_teachers`
(`hx-include` keeps the boxes already ticked).

### Grade entry (`grades/entry/`)

Same pattern with four selects: year → class → subject → period (the four
bimesters plus "Recuperação final"). A bimester sheet has every exam type but
the `C` ones; the final recovery sheet has only the `C` ones and only the
students whose annual average is below 6 (`annual_averages()`), with their
average and resulting final grade.
`GradeEntryOptionsView` re-renders the class, subject and bimester selects
(`#grade-selects`) when the year or class changes, clears `#search-results`
out of band and pushes `?school_year=&school_class=`. `grade_selection()`
drops a class that isn't in the chosen year and a subject the class's series
doesn't have. Subject and bimester load the sheet (`GradeEntryView`) into
`#search-results`.

The sheet is `GradeSheetForm`: one optional `DecimalField` (comma decimals)
per active enrollment × exam type, named `score_<enrollment>_<exam type>`.
On POST, any invalid cell saves nothing; otherwise `save()` creates, updates
or (for an emptied cell) deletes grades in one transaction, then redirects to
the same URL.

The report card (`grades/report_card/<enrollment pk>/`) is linked from the
enrollment list.

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

Sober and institutional: slate neutrals, white surfaces on a light canvas, one
deep red (`red-700`) for the brand, the current menu entry and destructive
actions. One typeface, **Public Sans**, for everything; titles stand out by size
and weight only. One icon set, **Material Symbols Outlined** (weight 300).
Shared classes live in `base.html` (`@layer components`); daisyUI is themed
there too, so form widgets, badges and modals follow the palette without extra
classes. Match the reference set `accounts/templates/suppliers/`; don't
introduce new colors or components without a reason.

### Layout (`base/templates/base/`)

- `base.html`: loads the CDNs and fonts, defines the shared classes and the
  daisyUI theme, positions row-menu popovers, and includes
  `sidebar/sidebar.html`, `navbar/navbar.html`, `messages.html` (toasts) and
  `sidebar/js/sidebar_js.html`. Blocks: `title`, `page_title` (the browser
  tab; default "Gestão Escolar"), `extra_head`, `header` (page heading, main
  action and search), `content`, `extra_js`. Content is capped at `max-w-7xl`
  on a `bg-slate-50` canvas.
- `navbar/navbar.html`: menu toggle and the global student search (GET to
  `students:student_list` with `q`; Ctrl/⌘ K focuses it).
- `messages.html`: flash messages as toasts, bottom right. Success and warning
  leave after 6 s; errors stay until closed.
- `sidebar/sidebar.html`: school logo, one `<details class="nav-group">` file
  per section from `sidebar/menu/` (`recursos_humanos.html`,
  `configuracao_de_matricula.html`, `financeiro.html`, `academico.html`,
  `itinerarios.html`), user menu with "Sair" and the version. Off-canvas
  below `lg`.
  - Each entry is
    `{% include 'base/sidebar/items/menu_item.html' with path="app:name" label="…" icon="…" %}`,
    where `icon` is a [Material Symbols](https://fonts.google.com/icons) name.
    The entry is marked `active` (`aria-current="page"`) on its URL and on the
    `add/`, `edit/`, `delete/`, `detail/` pages next to a `list/` URL
    (`{% nav_active %}` in `base/templatetags/ui.py`); the sidebar script opens
    the sections that hold it.
  - **Acadêmico** nests the **Edição** submenu (`academico_edicao.html`:
    Turmas, Departamentos, Matérias, Matérias por série, Tipos de avaliação,
    Tipos de ocorrência) above Lançamento de notas, Notas do aluno, Grade
    horária, Diário de classe, Ocorrências, Atrasos, Saídas para banheiro,
    Plantões, Matrículas, Alunos and Responsáveis.

  Add a new entry in the style of its section. `base/templates/base/sidebar.html`
  (no subfolder) is the old copy and is no longer included anywhere.

### Page patterns

| Page | Structure |
|---|---|
| List | `header`: `<div class="flex flex-wrap items-end justify-between gap-4 pb-6">` with `components/page/heading.html` (`section=` sidebar section, `title=`, optional `subtitle=`) and the main action as `button/button_primary.html` with `icon='add'` and a label naming the thing ("Novo fornecedor"), then `filter_form.html` with a `placeholder` naming the searchable fields. `content`: `<div id="search-results">{% include partial %}</div>` |
| List partial | `<div class="table-wrap"><table class="data-table">`, plain `<th>`/`<td>` (add only `text-right`, `whitespace-nowrap`), first column is the record's name and links to its edit page, secondary facts in a muted second line, last column `table/row_menu.html`. Ends with `table/pagination.html` |
| Add / edit (reference) | `<div class="page-form">`, `page/breadcrumb.html` (list → "Novo" or the record), `heading.html` with an action title ("Novo fornecedor", "Editar fornecedor"), then the form: `.form-section` blocks (intro `h2` + one-line `p` on the left, `.form-section-body` card with a field grid on the right) and a sticky `.form-actions` bar with Cancelar + "Salvar <coisa>" |
| Add / edit (older pages) | `page-form` (or `page-form-wide` when the form holds a table): `page-context` line "Gerenciamento de …" over a `page-title` h1, then `<thing>_form.html` in a `form-card`. Side-by-side fields go in `flex w-full flex-col gap-x-4 sm:flex-row` rows. Move a set to the reference pattern when you touch it |
| Delete | normally the row menu's dialog; the delete page stays as a fallback: breadcrumb, "Deletar <coisa>?" title, a `form-card` naming the record, cancel + `button_delete_form.html` |

### Components (`base/templates/components/`)

| Component | Use |
|---|---|
| `page/heading.html` | page h1; `title`, optional `section` (line above) and `subtitle` |
| `page/breadcrumb.html` | `parent_label`, `parent_url_name`, `current` |
| `form/field.html` | label (adds "(opcional)" when the field isn't required), widget, help text, errors. Use for every form field |
| `form/checkbox.html`, `form/checkbox_list.html` | checkbox with label; multiple-choice grid |
| `button/button_primary.html` | main page action, wrapped in `<a>`; optional `icon` |
| `button/button_submit_form.html` | primary submit |
| `button/button_delete_form.html` | destructive submit (red-700) |
| `button/button_select.html` | secondary button wrapped in `<a>` (Editar, Baixar…); label "Deletar" renders red; `size='small'` |
| `button/button_cancel.html` | cancel, wrapped in `<a>` back to the list |
| `search/search_input.html` | search only |
| `search/filter_form.html` | search + a "Filtros" button that opens the view's `filter_form` grid (open, with a count, while filters are active) + "Limpar filtros" |
| `table/row_menu.html` | "⋯" popover with Editar and Deletar; Deletar opens a `<dialog>` that posts to the delete view. Params: `menu_id` (pk), `edit_url`, `delete_url`, `delete_title`, `name`, `detail` |
| `table/pagination.html` | "Mostrando X–Y de N" + page numbers (htmx, `{% querystring %}`) |
| `table/empty_table.html` | empty state row; pass `collspan` (sic) |

Buttons in templates outside these components use the classes directly:
`ui-btn` plus `ui-btn-primary`, `ui-btn-secondary`, `ui-btn-danger` or
`ui-btn-danger-text`, optionally `ui-btn-sm`; icon-only buttons use
`ui-icon-btn` with an `aria-label`. Inside `.data-table` buttons shrink
automatically.

### Visual rules

- **Palette:** slate neutrals (`slate-900` text, `slate-500` secondary,
  `slate-200` lines, `slate-800` primary buttons). `red-700` for the brand,
  the active menu entry and destructive actions; `green-700` for success and
  receivables; `amber-700` for warnings.
- **Type:** Public Sans. Page title 28px semibold (`page-title`), section
  titles 15px semibold, labels 13px semibold, body 14px. Sentence case
  everywhere; no all-caps labels.
- **Tables:** `.data-table` (in `.table-wrap`): 13px muted headers, first
  column emphasized, `tabular-nums`, hover row. Money and numbers are
  right-aligned and `whitespace-nowrap`. Overdue installments show a red date
  with "Vencida" under it; the row itself isn't tinted.
- **Totals:** one bordered panel split into cells (see
  `installments/partials/installment_table.html`), numbers in `slate-900`,
  direction shown by a small colored dot.
- **Badges** (daisyUI `badge badge-sm`, restyled as soft pills in `base.html`):
  receivable = `badge-success badge-outline`, payable = `badge-error
  badge-outline`; installment status paid = `badge-success`, partial =
  `badge-warning`, cancelled = `badge-ghost`, expired = `badge-error`, open =
  `badge-neutral badge-outline`; delay tolerado = `badge-neutral
  badge-outline`, não tolerado = `badge-error`.
- **Form widgets** (set in the form's `widgets`): `input input-neutral w-full`,
  `select select-neutral w-full`, `textarea textarea-neutral w-full`; add
  `-sm` / `select-sm` in filter forms. Dates use `date_input()` in
  `accounts/forms.py` (`type="date"`, ISO format). Fields with errors get a
  red border from `aria-invalid`.
- **Formatting:** dates `|date:"d/m/Y"`; money `R$ {{ value|floatformat:"2g" }}`
  (thousands separator; keep plain `floatformat:2` in attributes and
  `value=`s); ordinals `{{ n }}ª`; CPF/CNPJ `{{ value|document }}` and
  `{{ value|person_kind }}` (`{% load ui %}`).
- **Flash messages** after every create/update/delete:
  "Registro cadastrado com sucesso" (success), "Registro atualizado com
  sucesso" (success), "Registro deletado com sucesso" (warning), errors as
  `messages.error`. They render as toasts.

## Configuration

- `config/settings.py` reads `SECRET_KEY`, `DJANGO_DEBUG` and `DATABASE_URL`
  from `.env` (python-dotenv). With debug on it uses `db.sqlite3`; with debug
  off, PostgreSQL from `DATABASE_URL` (schema `django_app`).
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
class roster page and its year → class select, and `grades/tests.py` the
averages, report card, exam types, series subjects and grade entry, and
`departments/tests.py` the department screens, and `incidents/tests.py` the
incident, incident type, delay and bathroom permission screens, and
`q_and_a/tests.py` the Q&A session screens, `pathways/tests.py` the
pathway rules, the extra grade and its settings screen, `lessons/tests.py` the
timetable and class diary rules and screens, and `employees/tests.py` the role
screens. `base/tests.py` also runs `full_seed` for a past and a future year.
`programs` and `students` have no tests yet. htmx requests are simulated with
`HTTP_HX_REQUEST="true"`. New features should come with tests in the same
style.

## Known issues and technical debt

- **No authorization.** Login is required everywhere, but users, groups and
  permissions are only managed, never checked: any logged-in user can open
  every screen (the "Professor" group `full_seed` creates is not enforced).
- **Production hardening is incomplete:** CDN assets aren't pinned or
  self-hosted.
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
