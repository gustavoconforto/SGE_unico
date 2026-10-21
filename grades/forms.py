from django import forms
from django.db import transaction
from django.urls import reverse

from employees.models import Employee
from grades.models import (
    FINAL_RECOVERY,
    ExamType,
    Grade,
    GradeLevel,
    GradeLevelSubject,
    Subject,
)
from grades.services import (
    annual_averages,
    bimester_grade,
    final_grade,
    needs_recovery,
    recovery_score,
)


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ["name", "department"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input input-neutral w-full"}),
            "department": forms.Select(attrs={"class": "select select-neutral w-full"}),
        }


class ExamTypeForm(forms.ModelForm):
    class Meta:
        model = ExamType
        fields = ["name", "code", "kind", "max_score", "order"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input input-neutral w-full"}),
            "code": forms.TextInput(attrs={"class": "input input-neutral w-full"}),
            "kind": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "max_score": forms.NumberInput(
                attrs={"class": "input input-neutral w-full", "step": "0.01"}
            ),
            "order": forms.NumberInput(attrs={"class": "input input-neutral w-full"}),
        }

    def clean_code(self):
        return self.cleaned_data["code"].upper()


class GradeLevelSubjectForm(forms.ModelForm):
    class Meta:
        model = GradeLevelSubject
        fields = ["grade_level", "subject", "teachers", "weekly_classes"]
        widgets = {
            "grade_level": forms.Select(
                attrs={"class": "select select-neutral w-full"}
            ),
            "subject": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "teachers": forms.CheckboxSelectMultiple(
                attrs={"class": "checkbox checkbox-sm checkbox-neutral"}
            ),
            "weekly_classes": forms.NumberInput(
                attrs={"class": "input input-neutral w-full", "step": "0.01"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only the teachers of the subject's department can be picked; choosing
        # another subject reloads the checkboxes (GradeLevelSubjectTeachersView).
        subject = self.selected_subject()
        department = subject.department if subject else None
        teachers = self.fields["teachers"]
        teachers.queryset = (
            department.teachers.order_by("name")
            if department
            else Employee.objects.none()
        )
        if subject is None:
            teachers.help_text = "Selecione a matéria para ver os professores."
        elif department is None:
            teachers.help_text = (
                f"A matéria {subject} não está vinculada a um departamento."
            )
        else:
            teachers.help_text = f"Professores do departamento {department}."
        self.fields["subject"].widget.attrs.update(
            {
                "hx-get": reverse("grades:grade_level_subject_teachers"),
                "hx-trigger": "change",
                "hx-target": "#teachers-field",
                "hx-swap": "outerHTML",
                "hx-include": "[name='teachers']",
            }
        )

    def selected_subject(self):
        if self.is_bound:
            value = self.data.get(self.add_prefix("subject"))
        else:
            value = self.initial.get("subject")
        value = getattr(value, "pk", value)
        if not str(value or "").isdigit():
            return None
        return Subject.objects.select_related("department").filter(pk=value).first()

    def clean(self):
        cleaned_data = super().clean()
        grade_level = cleaned_data.get("grade_level")
        subject = cleaned_data.get("subject")
        if (
            grade_level
            and subject
            and GradeLevelSubject.objects.filter(
                grade_level=grade_level, subject=subject
            )
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            self.add_error("subject", "Esta matéria já está cadastrada nesta série.")
        return cleaned_data


class GradeLevelSubjectFilterForm(forms.Form):
    grade_level = forms.TypedChoiceField(
        label="Série",
        required=False,
        coerce=int,
        empty_value=None,
        choices=[("", "Todas"), *GradeLevel.choices],
        widget=forms.Select(attrs={"class": "select select-neutral select-sm w-full"}),
    )


class GradeSheetForm(forms.Form):
    """Every score of one subject and bimester for a class: a row per enrollment
    and a column per exam type. Blank cells delete the grade.

    For the final recovery, only the enrollments whose annual average is below
    the passing grade get a row.
    """

    def __init__(self, *args, enrollments, exam_types, subject, bimester, **kwargs):
        super().__init__(*args, **kwargs)
        self.enrollments = list(enrollments)
        self.is_recovery = bimester == FINAL_RECOVERY
        self.averages = {}
        if self.is_recovery:
            self.averages = annual_averages(self.enrollments, subject)
            self.enrollments = [
                enrollment
                for enrollment in self.enrollments
                if needs_recovery(self.averages[enrollment.pk])
            ]
        self.exam_types = list(exam_types)
        self.subject = subject
        self.bimester = bimester
        self.existing = {
            (grade.enrollment_id, grade.exam_type_id): grade
            for grade in Grade.objects.filter(
                enrollment__in=self.enrollments, subject=subject, bimester=bimester
            ).select_related("exam_type")
        }
        for enrollment in self.enrollments:
            for exam_type in self.exam_types:
                grade = self.existing.get((enrollment.pk, exam_type.pk))
                self.fields[self.field_name(enrollment, exam_type)] = (
                    forms.DecimalField(
                        label=f"{enrollment.student} - {exam_type.code}",
                        required=False,
                        min_value=0,
                        max_value=exam_type.max_score,
                        max_digits=4,
                        decimal_places=2,
                        localize=True,
                        initial=grade.score if grade else None,
                        widget=forms.TextInput(
                            attrs={
                                "class": "input input-neutral input-sm w-20 text-right",
                                "inputmode": "decimal",
                            }
                        ),
                    )
                )

    @staticmethod
    def field_name(enrollment, exam_type):
        return f"score_{enrollment.pk}_{exam_type.pk}"

    def rows(self):
        """(enrollment, bound fields in exam type order, annual average, saved
        grade): the bimester grade, or the final grade after recovery."""
        grades_by_enrollment = {}
        for (enrollment_id, _), grade in self.existing.items():
            grades_by_enrollment.setdefault(enrollment_id, []).append(grade)
        for enrollment in self.enrollments:
            grades = grades_by_enrollment.get(enrollment.pk, [])
            fields = [
                self[self.field_name(enrollment, exam_type)]
                for exam_type in self.exam_types
            ]
            if self.is_recovery:
                average = self.averages[enrollment.pk]
                yield (
                    enrollment,
                    fields,
                    average,
                    final_grade(average, recovery_score(grades)),
                )
            else:
                yield enrollment, fields, None, bimester_grade(grades)

    @transaction.atomic
    def save(self):
        for enrollment in self.enrollments:
            for exam_type in self.exam_types:
                score = self.cleaned_data[self.field_name(enrollment, exam_type)]
                grade = self.existing.get((enrollment.pk, exam_type.pk))
                if score is None:
                    if grade:
                        grade.delete()
                elif grade is None:
                    Grade.objects.create(
                        enrollment=enrollment,
                        subject=self.subject,
                        exam_type=exam_type,
                        bimester=self.bimester,
                        score=score,
                    )
                elif grade.score != score:
                    grade.score = score
                    grade.save(update_fields=["score", "updated_at"])
