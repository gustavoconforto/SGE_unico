# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Staff of Único Educacional, working mostly at office desktops at the school:

- **Secretaria:** enrollments, students, guardians, required documents.
- **Financeiro:** receivables, payables, installments, payments, Bradesco bank slips (remittance and return files).
- **Coordenação/direção:** classes, subjects, timetable, grades and report cards, incidents, delays, Q&A sessions, pathways.
- **Professores:** grade entry, class diary, attendance.

Many are not technical and should be able to use the system without training. Mobile use is rare.

## Product Purpose

Gestão Escolar replaces a commercial school system Único disliked and that did not fit its rules. It puts student, family, academic and financial records in one place.

Success means:
- routine work (enrollment, payment posting, grade entry) takes less time and fewer steps;
- staff find what they need in one place instead of scattered tools;
- non-technical staff can use it without training.

## Positioning

Built around Único's own rules, which generic school systems don't handle: its programs (Ensino Médio, Pré UNB, Pré ENEM), extra-curricular pathways (itinerários) with an extra grade, separate discount groups for the first and remaining installments, enrollment contracts that generate their own receivables, and direct Bradesco CNAB 400 bank slips.

It starts as Único's in-house system. Offering it to other schools later is possible but not decided. Until then, avoid hard-coding Único-specific identity where it costs nothing to keep it configurable, but don't build multi-tenancy ahead of need.

## Operating Context

- Server-rendered Django app in Brazilian Portuguese. Code and docs are in English (see CLAUDE.md, ARCHITECTURE.md).
- The work is organized by sidebar sections: Recursos Humanos, Configuração de matrícula, Acadêmico, Financeiro, Itinerários.
- Daily rituals: enrolling a student (which creates the account and monthly installments), posting payments, generating remittance files and importing bank returns, entering grades per bimester, keeping the class diary and conduct records.
- The school year is split into four bimesters. Lessons run Monday to Saturday.
- A user manual in Portuguese lives in `doc/`. A test script for the enrollment flow is in `docs/roteiro-de-teste-matricula.pdf`.

## Capabilities and Constraints

- Every screen requires login. Users, groups and permissions are managed but **not yet enforced**, so any user sees every screen. Role-based access is an open item.
- The finance rules in CLAUDE.md and ARCHITECTURE.md are product truth: money correctness comes before speed or convenience.
- Front end is htmx + Tailwind 4 + daisyUI 5 from CDN, with no build step. Desktop-first. Layouts must still work at small widths (the sidebar goes off-canvas below `lg`), but they aren't designed for phones.
- Undecided: whether and when to offer the system to other schools.

## Brand Commitments

- Name: **Gestão Escolar**, for **Único Educacional** (school logo in `assets/`).
- Voice: plain, sober and institutional Brazilian Portuguese in sentence case, with standard flash messages ("Registro cadastrado com sucesso", …).
- An existing design system is documented in ARCHITECTURE.md ("Design system"), with `accounts/templates/suppliers/` as the reference set. It isn't recorded in a DESIGN.md yet.

## Evidence on Hand

- Development data from `manage.py full_seed` (a whole school year). It is fake and must not be shown as real figures.
- No testimonials, metrics or user research exist. Don't invent them.

## Product Principles

1. **Fit the school's real rules.** Model what Único actually does rather than generic school-software patterns.
2. **Fewer steps for routine work.** Optimize the frequent flows (enrollment, payments, grade entry) before the rare ones.
3. **One record, one place.** A student's academic, family and financial facts connect to each other; don't make people re-type or go looking.
4. **Obvious to non-technical staff.** Clear labels, predictable patterns and forgiving flows. Familiar beats clever.
5. **Trustworthy numbers.** Financial values are always correct and clearly explained.

## Accessibility & Inclusion

Formal requirement exists, but which standard applies is **undecided** (candidates: LBI via WCAG 2.1 AA, WCAG 2.2 AA, eMAG). Until it is confirmed, target WCAG 2.1 AA. Non-technical users need clear labels, readable text and forgiving error handling.
