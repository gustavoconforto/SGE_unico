---
target: sidebar and forms
total_score: 22
max_score: 40
na_heuristics: 
p0_count: 1
p1_count: 3
target_identity: "file:/Users/conforto/programacao/unico/django/gestao/base/templates/base/sidebar/sidebar.html"
target_fingerprint: "sha256:adbaebd26b88d95c058eebd8b3e7d5f50d2104d5decaad310002dab2d0cca710"
target_path: /Users/conforto/programacao/unico/django/gestao/base/templates/base/sidebar/sidebar.html
timestamp: 2026-11-07T23-11-43Z
slug: base-templates-base-sidebar-sidebar-html
---
# Critique: sidebar and forms — 22/40 (Acceptable)

Heuristics: 1 Status 2 · 2 Real world 3 · 3 Control 2 · 4 Consistency 2 · 5 Error prevention 2 · 6 Recognition 2 · 7 Efficiency 2 · 8 Minimalism 3 · 9 Error recovery 2 · 10 Help 2.

Specificity: the copy is specific to Único (section intros); the visual shell is a generic slate admin and the sidebar follows the code's apps rather than staff jobs.
Detector: sidebar clean; forms 1 CLI hit (oversized-h1 in preview_enrollment.html, false positive); browser: placeholder contrast 3.4:1 (#878b95), a nested card on guardian rows, a straggler line in the student form intro, red-100 on red text on the login page 3.9:1.

## Priority issues
- [P0] enrollment_form.html:89 renders `{{ installment.type }}`, so the documents checklist has blank names and unlabelled checkboxes. Fix: `{{ f.instance.type }}` + label. (harden)
- [P1] field.html: help/error <p> lack the ids that the inputs' aria-describedby point to; icon ligatures ("error", "expand_more", "school") read aloud — add aria-hidden. (harden)
- [P1] Off-canvas sidebar stays in tab order when closed (only translated); toggle lacks aria-expanded; .ui-icon-btn has no focus-visible style. Fix: `inert` in setMobileOpen. (harden)
- [P1] Input border #cbd5e1 ≈1.5:1 fails WCAG 1.4.11; focus halo at 14% opacity. Fix: slate-500 border, solid 2px focus ring. (audit/polish)
- [P2] Enrollment add: no preview of instalment values before a write that creates money; 94/121-option selects with no search; Cancelar → classes:class_list; English "Select an option". (clarify/onboard)
- [P2] Sidebar IA: Acadêmico holds 24 entries incl. Itinerários and the secretaria's daily screens at the bottom; duplicate icon in Duplicatas; nested headers barely distinct. (distill/layout)

## Persona red flags
Alex: no jump-to-screen, scroll-selects, focus lost after failed submit. Sam: hidden links focusable, ligatures read, broken describedby, unlabelled checkboxes, weak borders. Jordan: Matrículas buried, "Criar itinerário" opens a list, "Digite..." placeholders, required docs revealed only after submit.
