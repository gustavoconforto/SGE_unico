# Testing roadmap

A step-by-step guide for testing Gestão Escolar by hand, from an empty database
to a full school year: people, enrollments, classes, grades, pathways, finance
and bank slips.

The order matters. Most records depend on others (an enrollment needs a
student, a student needs a financial guardian, a contract needs a course and a
school year…), so each phase only uses data created in the phases before it.
Follow the phases in order the first time; after that, any phase can be
re-tested on its own.

Screen names below are the labels in the sidebar (the UI is in Portuguese).
Paths are relative to the server address, e.g. `http://127.0.0.1:8000`.

---

## How to use this guide

- Tick the checkboxes as you go. Each phase has:
  - **Create**: the records to insert, with sample data.
  - **Check**: what should happen if the system works.
  - **Try to break it**: invalid input that should be refused with a clear
    message, not an error page.
- Every create, edit and delete should show a toast in the bottom-right corner:
  "Registro cadastrado com sucesso", "Registro atualizado com sucesso" or
  "Registro deletado com sucesso". A missing toast is worth reporting.
- An error page ("Server Error (500)" or a yellow Django debug page) is
  **always** a bug. Write down the URL and what you typed.
- Report anything confusing too: unclear labels, missing fields, wrong
  wording, layout problems on a phone. Those are "changes to be made", not only
  bugs.

### Reporting an issue

Use this template for every finding:

```
Phase / step:     e.g. 6.2 Matrícula
Screen (URL):     /enrollments/add/
What I did:       chose student X, contract Y, class Z, saved
What I expected:  enrollment saved with 10 installments
What happened:    only 9 installments / error page / confusing message
Type:             bug | wording | layout | suggestion
Screenshot:       (attach)
```

---

## Dependency map

What has to exist before you can create each record:

```
Usuários, Grupos, Permissões                  (independent)

Cargos ──▶ Funcionários ──▶ Departamentos ──▶ Matérias ──▶ Matérias por série
                                                              │
Ano escolar ─┬──▶ Turmas ◀── Cursos oferecidos                │
             │       │                                        ▼
             └──▶ Contratos ◀── Cursos              Grade horária / Diário de classe
                     │
Descontos ───────────┤        Documentos (checklist created with each enrollment)
                     ▼
Responsáveis ──▶ Alunos ──▶ Matrículas ──┬──▶ Conta a receber + Parcelas (automatic)
 (financial)                             ├──▶ Notas, Boletim
                                         ├──▶ Ocorrências, Atrasos, Saídas, Plantões
                                         └──▶ Inscrições em itinerário

Tipos de avaliação ──▶ Lançamento de notas
Tipos de ocorrência ──▶ Ocorrências ──▶ Nota de conceito (code C)
Itinerários ──▶ Turmas de itinerário ──▶ Inscrições ──▶ Aulas e chamadas ──▶ Notas de itinerário ──▶ Nota extra (code EX)

Categoria financeira ──┬──▶ Contratos a receber ──▶ Parcelas ──▶ Baixas
Fornecedores ──────────┴──▶ Contratos a pagar   ──▶ Parcelas ──▶ Pagamentos
Configuração bancária ──▶ Remessas ──▶ Boletos ──▶ Retornos
```

---

## Phase 0 — Environment and login

- [ ] Start the server: `uv run python manage.py runserver`.
- [ ] Create a login if there is none: `uv run python manage.py createsuperuser`.
- [ ] Open `/` while logged out → you are sent to `/login/`.
- [ ] Log in with a wrong password → error message, no error page.
- [ ] Log in with the right password → home page with the sidebar.
- [ ] Open the user menu at the bottom of the sidebar → "Sair" logs you out.
- [ ] Press Ctrl+K (⌘K on Mac) → the student search at the top gets focus.

> Two shortcuts exist, but skip them on the first pass so every screen gets
> tested by hand:
> - `uv run python manage.py clean` **inserts** reference data (courses, school
>   years, classes, contracts, discounts, documents, roles) despite its name.
> - `uv run python manage.py full_seed` **erases the whole database** and fills
>   a complete school year. Use it only for Phase 15.

---

## Phase 1 — Administration (sidebar: Recursos humanos)

Screens: **Usuários** (`/users/`), **Grupos** (`/groups/`),
**Permissões** (`/permissions/`).

**Create**
- [ ] Group "Secretaria".
- [ ] User "secretaria1" in the group "Secretaria".

**Check**
- [ ] Log out and log in as "secretaria1".
- [ ] Note which screens this user can open. Known limitation: permissions are
      saved but **not enforced yet**, so every logged-in user sees everything.
      Note it, but no need to report it again.

**Try to break it**
- [ ] Create a user with an existing username.
- [ ] Delete a group that has users.

---

## Phase 2 — Staff (sidebar: Recursos humanos)

### 2.1 Cargos (`/employees/roles/list/`)

**Create**
- [ ] "PROFESSOR"
- [ ] "COORDENADOR"

### 2.2 Funcionários (`/employees/list/`)

Needs: a role.

**Create** at least four teachers (role "PROFESSOR"). Teachers are needed for
departments, subjects, timetables and pathways later.

| Nome | CPF | RG | Órgão expedidor |
|---|---|---|---|
| Ana Matemática | 11111111111 | 1111111 | SSP/DF |
| Bruno Português | 22222222222 | 2222222 | SSP/DF |
| Carla Física | 33333333333 | 3333333 | SSP/DF |
| Diego História | 44444444444 | 4444444 | SSP/DF |

**Check**
- [ ] The list search finds a teacher by name.
- [ ] Ticking "Pode acessar o SUGA" and typing a password saves; editing the
      employee again does not show the password in plain text.

**Try to break it**
- [ ] Save an employee with a CPF or RG already used by another employee.
- [ ] CPF with dots and dash (`111.111.111-11`).
- [ ] Delete the role "PROFESSOR" while employees use it → blocked with a
      message.

---

## Phase 3 — School year and enrollment settings (sidebar: Configuração de matrícula)

### 3.1 Ano escolar (`/enrollments/school-years/list/`)

**Create** the current year, with the four bimesters filled in (the concept
grade, extra grade and Q&A points only work when the bimester dates exist):

| Field | Value |
|---|---|
| Início / Fim | 02/02/2026 – 18/12/2026 |
| 1º bimestre | 02/02 – 24/04 |
| 2º bimestre | 27/04 – 10/07 |
| 3º bimestre | 27/07 – 02/10 |
| 4º bimestre | 05/10 – 18/12 |

- [ ] Also create next year (2027) to test enrolling ahead.

**Try to break it**
- [ ] End date before the start date; a bimester outside the year; bimesters
      overlapping. Note whether the system accepts it (a suggestion if it does).

### 3.2 Cursos oferecidos (`/programs/list/`)

- [ ] Create "Ensino Médio" and "Pré ENEM".
- [ ] Try to create "Ensino Médio" again → refused (name is unique).

### 3.3 Documentos (`/enrollments/needed-documents/list/`)

- [ ] Create "CERTIDÃO DE NASCIMENTO", "COMPROVANTE DE RESIDÊNCIA",
      "CPF DO RESPONSÁVEL". Every new enrollment gets one checklist row per
      document type.

### 3.4 Descontos (`/enrollments/discount-types/list/`)

- [ ] Create "IRMÃOS" 10% and "FILHO DE FUNCIONÁRIO" 50%.
- [ ] Try 150% and -5% → refused (0 to 100).

### 3.5 Turmas (sidebar: Acadêmico › Edição › Turmas, `/classes/list/`)

Needs: course and school year.

**Create**
- [ ] "Aplicação" — Ensino Médio, 2026, série 1, turno Manhã, 30 vagas.
- [ ] "Brio" — Ensino Médio, 2026, série 2, turno Manhã, 30 vagas.
- [ ] "Extensivo" — Pré ENEM, 2026, no série, turno Noite.

**Try to break it**
- [ ] A second "Aplicação" in Ensino Médio 2026 → refused (unique per year and
      course).

### 3.6 Contratos (`/enrollments/enrollment-types/list/`)

Needs: course and school year.

**Create**
- [ ] Ensino Médio, 1ª série, 2026, valor total R$ 12.000,00, desconto de
      pontualidade R$ 90,00.
- [ ] Ensino Médio, 2ª série, 2026, R$ 12.600,00.
- [ ] Ensino Médio, 1ª série, **2027**, R$ 13.000,00.

**Check**
- [ ] Start and end dates are filled from the school year when left empty.

---

## Phase 4 — Academic setup (sidebar: Acadêmico › Edição)

### 4.1 Departamentos (`/departments/list/`)

Needs: employees.

- [ ] "Exatas" with Ana and Carla; "Humanas" with Bruno and Diego.
- [ ] Put one teacher in two departments → allowed.

### 4.2 Matérias (`/grades/subjects/list/`)

- [ ] Matemática (Exatas), Física (Exatas), Português (Humanas),
      História (Humanas).
- [ ] Try to delete "Exatas" now → blocked, subjects use it.
- [ ] Known gap: this screen shows no toast after saving. Note it.

### 4.3 Matérias por série (`/grades/grade_level_subjects/list/`)

Needs: subjects with a department, and teachers in that department. Without
this, a class has **no subjects**: no grades, no timetable.

- [ ] Série 1: Matemática (teacher Ana, 5 aulas/semana), Português (Bruno, 5),
      Física (Carla, 3), História (Diego, 2).
- [ ] Série 2: the same subjects.

**Check**
- [ ] Changing the subject reloads the teacher checkboxes, showing only that
      subject's department teachers.
- [ ] Weekly classes accept decimals like 1,5.

**Try to break it**
- [ ] The same subject twice in the same series → "Esta matéria já está
      cadastrada nesta série."

### 4.4 Tipos de avaliação (`/grades/exam_types/list/`)

The codes **C** and **EX** are special: the system calculates them (concept and
extra grade). Create exactly these:

| Código | Nome | Tipo | Nota máxima | Ordem |
|---|---|---|---|---|
| PS | Prova de sala | Avaliação | 3 | 1 |
| PB | Prova bimestral | Avaliação | 6 | 2 |
| C | Conceito | Avaliação | 1 | 3 |
| EX | Nota extra | Ponto extra | 5 | 4 |
| A | Ajuste | Recuperação | 10 | 5 |

- [ ] Type the code in lowercase → saved uppercase.
- [ ] Max score 0 → refused.

### 4.5 Tipos de ocorrência (`/incidents/type/list/`)

- [ ] "Conversa excessiva" penalty 0,1; "Uso de celular em sala" 0,2;
      "Cola em avaliação" 0,5.
- [ ] Negative penalty → refused.

### 4.6 Turma detail (`/classes/detail/`)

- [ ] Pick 2026 → the class select only lists 2026 classes.
- [ ] Pick "Aplicação" → shows the series 1 subjects and teachers, and an
      empty student list (nobody enrolled yet).
- [ ] Reload the page → the selection is kept.

---

## Phase 5 — Guardians and students (sidebar: Acadêmico)

### 5.1 Responsáveis (`/students/guardians/list/`)

**Create**: the first one with a full address, because bank slips (Phase 13)
are only issued for guardians with a valid CPF, address and CEP.

| Nome | CPF | RG | Endereço | Cidade/UF | CEP |
|---|---|---|---|---|---|
| Maria Souza | 52998224725 | 5555555 | Quadra 1 Casa 2 | Brasília/DF | 70000000 |
| João Lima | 11144477735 | 6666666 | (empty) | | |

### 5.2 Alunos (`/students/list/`)

Needs: guardians. The student form has a tab for linking guardians.

**Create**
- [ ] "Pedro Souza": link Maria as **Mãe**, tick **Responsável financeiro** and
      **Contato principal**.
- [ ] "Lucas Souza" (Pedro's brother): link Maria as Mãe, financial.
- [ ] "Julia Lima": link João as Pai, **without** "Responsável financeiro"
      (used for a negative test in Phase 6).
- [ ] Upload a photo for Pedro.

**Check**
- [ ] The matrícula number is generated automatically (`2026` + 5 digits, e.g.
      `202600001`) and increases with each student.
- [ ] Photo appears on the list/edit page; a student without a photo shows a
      placeholder. Replacing the photo shows the new one.
- [ ] Fill "Nome social" and tick "Usar nome social" → the list shows the
      social name.
- [ ] The search box at the top of every page finds the student.

**Try to break it**
- [ ] Link the same guardian twice to one student → refused.
- [ ] Save a student with a CPF that another student already has.
- [ ] Delete a guardian linked to a student → blocked.
- [ ] Submit the form with an error on the guardian tab → the page should open
      on the tab with the error.

---

## Phase 6 — Enrollments (sidebar: Acadêmico › Matrículas, `/enrollments/list/`)

Needs: student **with a financial guardian**, contract, (optional) class,
(optional) discount, documents.

### 6.1 Create

- [ ] Pedro → contract "Ensino Médio 1ª série 2026" → class "Aplicação",
      dia de vencimento 10.
- [ ] Lucas → "Ensino Médio 2ª série 2026" → class "Brio", discount "IRMÃOS".
- [ ] One student enrolled **ahead** in "Ensino Médio 1ª série 2027" (no class
      needed).

### 6.2 Check

- [ ] Choosing the contract reloads the class select with only classes of the
      same year, course and série, each showing "(enrolled/capacity)".
- [ ] Valor bruto, percentual de desconto and data da matrícula are filled
      automatically and read-only.
- [ ] Edit page shows the **documents checklist** (one row per document type)
      and the **installments**.
- [ ] Installments, enrolled during the year: the first is due on the enrollment
      date, the rest on day 10 of each month through December; a day 10 on a
      weekend moves to Monday.
- [ ] Installments, enrolled ahead (2027): 12 installments, the first on the
      enrollment date, then February to December 2027.
- [ ] The installments add up exactly to the net value (Lucas: 12.600 − 10%).
- [ ] Contratos a receber (`/accounts/receivable/list/`) shows one new account
      per enrollment, category "Mensalidade", linked to the financial guardian.
- [ ] Tick a document as delivered, save → still ticked after reload.
- [ ] Print preview and PDF from the enrollment (`print/preview`, `print/pdf`).
- [ ] Change the contract price afterwards → existing enrollments keep their
      old value.
- [ ] Turma detail (Phase 4.6) for "Aplicação" now lists Pedro.

### 6.3 Try to break it

- [ ] Enroll Julia (no financial guardian) → "O aluno precisa ter ao menos um
      responsável financeiro cadastrado."
- [ ] Enroll Pedro again in the same contract → refused.
- [ ] Dia de vencimento 31 → refused (1 to 28).
- [ ] Fill a class above its capacity → note whether it's allowed.

### 6.4 Status change (do this at the end of testing, on a spare enrollment)

- [ ] Change an enrollment to "Desistente", "Transferida" or "Cancelada" →
      its **open** installments due today or later become "Cancelada"; paid and
      partially paid ones stay.

---

## Phase 7 — Timetable and class diary (sidebar: Acadêmico)

Needs: class with a série, subjects per série with teachers.

### 7.1 Grade horária (`/lessons/timetable/`)

- [ ] Pick "Aplicação" → empty 5 × 7 grid and the weekly load per subject.
- [ ] Edit: fill cells with "Matéria — Professor". Save.
- [ ] Weekly load shows a warning when the periods don't match "aulas/semana"
      (a warning, not an error).

**Try to break it**
- [ ] Put Ana in the same weekday and period in "Aplicação" and "Brio" (both
      Manhã, same year) → refused (teacher clash).
- [ ] Same clash with a class in another shift → allowed.
- [ ] One invalid cell → nothing saved.

### 7.2 Diário de classe (`/lessons/lectures/list/`, day sheet `/lessons/lectures/day/`)

- [ ] Open the day sheet for "Aplicação" on a weekday → rows prefilled from the
      timetable. Type a topic in some rows and save → only rows with a topic
      are saved.
- [ ] Change the teacher of one row (substitute) → the timetable is unchanged.
- [ ] Clear a topic → that lecture is deleted.
- [ ] The list filters by year, class, subject, teacher and dates; search by
      topic.

**Try to break it**
- [ ] A Saturday, or a date outside the school year → refused.
- [ ] A teacher from outside the subject's department → refused.

---

## Phase 8 — Daily student records (sidebar: Acadêmico)

Needs: active enrollments. All of these select an **enrollment**, and the
select only lists active ones.

- [ ] **Ocorrências** (`/incidents/list/`): two incidents for Pedro in the
      1st bimester (e.g. "Uso de celular em sala" twice).
- [ ] **Atrasos** (`/incidents/delay/list/`): four "tolerado" delays for Pedro
      in the 1st bimester; one "não tolerado".
- [ ] **Saídas para banheiro** (`/incidents/bathroom/list/`): one at aula 3.
      Try aula 0 → refused.
- [ ] **Plantões** (`/q_and_a/list/`): three Q&A sessions for Pedro in
      Matemática in the 1st bimester. Filter by subject and date range.

**Check**
- [ ] The enrollment of a cancelled student is not offered in these selects.
- [ ] Lists show the class next to the student and search by student name.

---

## Phase 9 — Grades (sidebar: Acadêmico)

Needs: enrollments with a class that has a série, subjects per série, exam
types.

### 9.1 Lançamento de notas (`/grades/entry/`)

- [ ] Pick year → class → subject → 1º bimestre. One row per active student,
      one column per exam type (except "Recuperação" types).
- [ ] Type PS 2,5 and PB 5 for Pedro → save → values kept after reload.
- [ ] Empty a cell and save → that grade is deleted.

**Try to break it**
- [ ] PS 4 (above max 3) → refused, and **nothing** on the sheet is saved.
- [ ] Negative or text values.

### 9.2 Concept grade (code C) — `/incidents/grades/all`

- [ ] Calculate the 1st bimester concept. Expected for Pedro:
      1 − (0,2 + 0,2) − 0,2 × (4 − 2 tolerated delays) = **0,20**.
      Non-tolerated delays don't change it.
- [ ] Students without incidents get 1,00.

### 9.3 Pathways and extra grade (code EX) — see Phase 10, then come back.

### 9.4 Notas do aluno (`/grades/entry/specific/`)

- [ ] Pick Pedro → edit one subject's grades for all bimesters in one row.

### 9.5 Boletim (from the enrollment list, `/grades/report_card/<id>/`)

- [ ] Bimester grade = PS + PB + C + EX, capped at 10.
- [ ] Annual average appears only when all 4 bimesters exist; weights 20%, 30%,
      20%, 30%; rounded to the half point.
- [ ] With an average below 6, the subject shows "Em recuperação"; the
      "Recuperação final" period in grade entry lists only those students.
      Final grade = (average + recovery) / 2, passing at 6.

---

## Phase 10 — Pathways (sidebar: Itinerários)

Needs: school year, teachers, active enrollments.

1. [ ] **Itinerários** (`/pathways/list/`): "Robótica", pontos extras 1,00.
2. [ ] **Turmas de itinerário** (`/pathways/offerings/list/`): Robótica 2026,
       teacher Carla, 2 vagas. Try 0 vagas → "Informe ao menos uma vaga."
3. [ ] **Inscrições** (`/pathways/enrollments/list/`): enroll Pedro and Lucas.
       A third student → refused (no seats). Set "saída" on Lucas → a seat
       frees up.
4. [ ] **Aulas e chamadas** (`/pathways/sessions/list/`): four lessons in the
       1st bimester. After saving each, the roll call opens with everyone
       present; mark Pedro absent once (75% attendance).
5. [ ] **Notas de itinerário** (`/pathways/grades/entry/`): Pedro 8,0 in the
       1st bimester → shows the attendance and the extra points (0,80).
6. [ ] **Regras da nota extra** (`/pathways/extra_grade_settings/list/`):
       defaults 75% attendance, 3 Q&A sessions, 0,50 points.
7. [ ] **Nota extra** (`/pathways/extra_grades/all/`): calculate the 1st
       bimester. Pedro: 0,80 (pathway) + 0,50 (3 plantões) = **1,30** in every
       subject's EX column.

**Try to break it**
- [ ] Mark Pedro absent twice (50%) and recalculate → pathway points drop to 0.
- [ ] Delete a pathway member that has attendance → blocked.
- [ ] Offering of 2027 with a 2026 enrollment → refused.

---

## Phase 11 — Finance setup (sidebar: Financeiro)

### 11.1 Categoria financeira (`/accounts/categories/list/`)

- [ ] "Mensalidade" already exists (created by the first enrollment).
- [ ] Create "Material didático" (A receber) and "Energia elétrica" (A pagar).
- [ ] Try to change the direction of "Mensalidade" → locked, accounts use it.

### 11.2 Fornecedores (`/accounts/suppliers/list/`)

- [ ] "Companhia de Energia", CNPJ 14 digits.
- [ ] CPF with 10 digits, or letters → "O CPF deve ter 11 dígitos e o CNPJ, 14."

---

## Phase 12 — Accounts, installments and payments (sidebar: Financeiro)

### 12.1 Contratos a receber (manual) (`/accounts/receivable/list/`)

- [ ] "Material didático" for Maria, R$ 1.000,00, desconto R$ 100,00,
      3 parcelas → 3 installments adding up to R$ 900,00.
- [ ] Discount greater than the gross value → refused.
- [ ] Edit the account → gross value and discount are locked.

### 12.2 Contratos a pagar (`/accounts/payable/list/`)

- [ ] "Conta de luz" for "Companhia de Energia", R$ 500,00, 1 parcela.

### 12.3 Parcelas (`/accounts/installments/list/`)

- [ ] Filter by status, direction and due date; an installment past due shows
      the date in red with "Vencida".
- [ ] Add an extra installment to an account without a number → gets the next
      number.

### 12.4 Baixa de matrícula (`/accounts/payments/add/`)

Use Pedro's first installment.

- [ ] Partial payment of half the amount → status "Parcialmente paga".
- [ ] Pay the rest with multa and juros: valor = balance + charges → "Paga".
- [ ] Delete that last payment → back to "Parcialmente paga".
- [ ] A payment bigger than the balance (without charges) → refused.
- [ ] A payment of zero → refused.

### 12.5 Pagamento de contas (`/accounts/payments/payable/add/`)

- [ ] Pay the "Conta de luz" installment → "Paga".

### 12.6 Protection

- [ ] Delete an account with payments → blocked with a message.
- [ ] Delete an account without payments → deleted with its installments.
- [ ] Delete a category or supplier in use → blocked.

---

## Phase 13 — Bank slips (sidebar: Financeiro)

Needs: receivable installments not yet due, with a financial guardian who has
a valid CPF, address and CEP (Maria).

1. [ ] **Configuração bancária** (`/billing/settings/edit/`): fill company
       code, agência, conta, dígito; carteira "09". Try letters or a 1-digit
       carteira → refused.
2. [ ] **Remessas** (`/billing/remittances/list/`) → new remittance:
       - Maria's children's installments are offered.
       - João's (no address) are listed but skipped.
       - Overdue installments are skipped.
       - Submitting with nothing selected → refused.
3. [ ] Download the `.REM` file. Remittance number increases by 1.
4. [ ] **Boletos** (`/billing/slips/list/`): one slip per installment, status
       "Gerado".
5. [ ] Create another remittance → the same installments are **not** offered
       again (they already have a live slip).
6. [ ] Delete the last remittance (bank hasn't processed it) → slips go away,
       number is freed.
7. [ ] **Retornos** (`/billing/returns/list/`): needs a `.RET` file from the
       bank. If you have one, import it and check the detail page; importing
       the same file twice must be refused.
8. [ ] Pay an installment in cash that has a registered slip → it appears as a
       write-off candidate in the next remittance.

---

## Phase 14 — Cross-cutting checks (on every list)

- [ ] Search updates the table as you type, without reloading the page.
- [ ] Filters: "Filtros" button shows the count of active filters;
      "Limpar filtros" resets them.
- [ ] Pagination (10 per page) keeps search and filters; reload and the back
      button keep the same page.
- [ ] Row menu "⋯" → Editar / Deletar; delete asks for confirmation.
- [ ] Deleting a record that others depend on shows a message, never an error
      page.
- [ ] Phone width (or a narrow window): sidebar collapses, tables scroll, forms
      readable.
- [ ] Dates shown as dd/mm/aaaa, money as R$ 1.234,56, CPF formatted.
- [ ] Session expired (log out in another tab), then use a search box → you
      are sent to the login page.

---

## Phase 15 — Volume test (optional)

Only on a throw-away database: this command **erases everything**.

```bash
uv run python manage.py full_seed
```

It creates 31 classes × 45 students and a full year of grades, incidents,
pathways, lectures, installments and bank slips.

- [ ] Lists still load fast; search and filters respond quickly.
- [ ] Report cards, grade entry sheets and class diary open for a big class.
- [ ] Finance totals look consistent (installment list totals vs. accounts).

---

## Deletion order (to clean up by hand)

Records are protected while something uses them. To delete everything by hand,
go in reverse: payments → bank slips/remittances → manual accounts → pathway
records → grades, incidents, Q&A → lectures, timetable → enrollments →
students → guardians → contracts, classes → subjects per series → subjects →
departments → employees → roles → school years, courses.
