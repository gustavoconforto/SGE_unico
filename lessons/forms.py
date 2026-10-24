from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from accounts.forms import date_input
from classes.models import Class
from employees.models import Employee
from enrollments.models import SchoolYear
from grades.models import GradeLevelSubject, Subject
from lessons.models import (
    PERIODS,
    Lecture,
    TimetableSlot,
    Weekday,
    lecture_date_error,
)

CELL = "select select-neutral select-sm w-full"


def series_classes():
    """Classes with a series: only they have subjects, so only they have lectures."""
    return (
        Class.objects.filter(grade_level__isnull=False)
        .select_related("year")
        .order_by("-year__begins", "grade_level", "name")
    )


def level_subjects(grade_level):
    return GradeLevelSubject.objects.filter(grade_level=grade_level).select_related(
        "subject"
    )


def level_teachers(grade_level):
    """The teachers of the series' subjects and of their departments."""
    return (
        Employee.objects.filter(
            Q(grade_level_subjects__grade_level=grade_level)
            | Q(departments__subjects__grade_level_subjects__grade_level=grade_level)
        )
        .distinct()
        .order_by("name")
    )


def class_field(empty_label="Selecione uma turma"):
    return forms.ModelChoiceField(
        label="Turma",
        required=False,
        queryset=series_classes(),
        empty_label=empty_label,
        widget=forms.Select(attrs={"class": "select select-neutral w-full"}),
    )


# TIMETABLE FORMS


class TimetableSelectForm(forms.Form):
    school_class = class_field()


class TimetableForm(forms.Form):
    """The class's whole timetable: one "Matéria — Professor" select per
    weekday and period. A blank cell has no lesson."""

    def __init__(self, *args, school_class, **kwargs):
        super().__init__(*args, **kwargs)
        self.school_class = school_class
        self.existing = {
            (slot.weekday, slot.period): slot
            for slot in school_class.timetable_slots.all()
        }
        self.options = {}
        choices = [("", "—")]
        for subject in level_subjects(school_class.grade_level).prefetch_related(
            "teachers"
        ):
            for teacher in subject.teachers.all():
                value = f"{subject.pk}-{teacher.pk}"
                self.options[value] = (subject, teacher)
                choices.append((value, f"{subject.subject.name} — {teacher.name}"))
        for weekday, weekday_label in Weekday.choices:
            for period, period_label in PERIODS:
                slot = self.existing.get((weekday, period))
                self.fields[self.field_name(weekday, period)] = forms.ChoiceField(
                    label=f"{weekday_label}, {period_label}",
                    required=False,
                    choices=choices,
                    initial=f"{slot.subject_id}-{slot.teacher_id}" if slot else "",
                    widget=forms.Select(attrs={"class": CELL}),
                )

    @staticmethod
    def field_name(weekday, period):
        return f"slot_{weekday}_{period}"

    def rows(self):
        """(period label, [bound field per weekday])."""
        for period, label in PERIODS:
            yield (
                label,
                [self[self.field_name(weekday, period)] for weekday in Weekday.values],
            )

    def clean(self):
        cleaned_data = super().clean()
        self.changed_slots = []
        self.removed_slots = []
        for weekday in Weekday.values:
            for period, _ in PERIODS:
                name = self.field_name(weekday, period)
                value = cleaned_data.get(name)
                slot = self.existing.get((weekday, period))
                if not value:
                    if slot:
                        self.removed_slots.append(slot)
                    continue
                subject, teacher = self.options[value]
                if slot is None:
                    slot = TimetableSlot(
                        school_class=self.school_class, weekday=weekday, period=period
                    )
                elif slot.subject_id == subject.pk and slot.teacher_id == teacher.pk:
                    continue
                slot.subject, slot.teacher = subject, teacher
                try:
                    slot.full_clean()
                except ValidationError as error:
                    self.add_error(name, error.messages)
                    continue
                self.changed_slots.append(slot)
        return cleaned_data

    @transaction.atomic
    def save(self):
        for slot in self.removed_slots:
            slot.delete()
        for slot in self.changed_slots:
            slot.save()


# LECTURE FORMS


class LectureDaySelectForm(forms.Form):
    school_class = class_field()
    date = forms.DateField(label="Data", required=False, widget=date_input())

    def clean(self):
        cleaned_data = super().clean()
        school_class, day = cleaned_data.get("school_class"), cleaned_data.get("date")
        if school_class and day:
            message = lecture_date_error(school_class, day)
            if message:
                self.add_error("date", message)
        return cleaned_data


class LectureDayForm(forms.Form):
    """The class's lectures on a date: a row per period, prefilled from the
    saved lecture or the timetable. Only rows with a topic are kept; clearing
    the topic deletes the lecture."""

    def __init__(self, *args, school_class, date, **kwargs):
        super().__init__(*args, **kwargs)
        self.school_class = school_class
        self.date = date
        self.existing = {
            lecture.period: lecture
            for lecture in Lecture.objects.filter(school_class=school_class, date=date)
        }
        planned = {
            slot.period: slot
            for slot in school_class.timetable_slots.filter(weekday=date.isoweekday())
        }
        # Plain choices, so the selects of the 7 rows share two queries.
        self.subjects = {
            subject.pk: subject for subject in level_subjects(school_class.grade_level)
        }
        self.teachers = {
            teacher.pk: teacher for teacher in level_teachers(school_class.grade_level)
        }
        subject_choices = [("", "—")] + [
            (pk, subject.subject.name) for pk, subject in self.subjects.items()
        ]
        teacher_choices = [("", "—")] + [
            (pk, teacher.name) for pk, teacher in self.teachers.items()
        ]
        for period, label in PERIODS:
            lecture = self.existing.get(period)
            source = lecture or planned.get(period)
            self.fields[f"subject_{period}"] = forms.TypedChoiceField(
                label=f"Matéria da {label}",
                required=False,
                coerce=int,
                empty_value=None,
                choices=subject_choices,
                initial=source.subject_id if source else None,
                widget=forms.Select(attrs={"class": CELL}),
            )
            self.fields[f"teacher_{period}"] = forms.TypedChoiceField(
                label=f"Professor da {label}",
                required=False,
                coerce=int,
                empty_value=None,
                choices=teacher_choices,
                initial=source.teacher_id if source else None,
                widget=forms.Select(attrs={"class": CELL}),
            )
            self.fields[f"topic_{period}"] = forms.CharField(
                label=f"Conteúdo da {label}",
                required=False,
                max_length=200,
                initial=lecture.topic if lecture else "",
                widget=forms.TextInput(
                    attrs={"class": "input input-neutral input-sm w-full"}
                ),
            )

    def rows(self):
        """(period label, subject, teacher and topic bound fields, saved?)."""
        for period, label in PERIODS:
            yield (
                label,
                self[f"subject_{period}"],
                self[f"teacher_{period}"],
                self[f"topic_{period}"],
                period in self.existing,
            )

    def clean(self):
        cleaned_data = super().clean()
        self.changed_lectures = []
        self.removed_lectures = []
        for period, _ in PERIODS:
            topic = cleaned_data.get(f"topic_{period}", "").strip()
            subject_id = cleaned_data.get(f"subject_{period}")
            teacher_id = cleaned_data.get(f"teacher_{period}")
            lecture = self.existing.get(period)
            if not topic:
                if lecture:
                    self.removed_lectures.append(lecture)
                continue
            if subject_id is None:
                self.add_error(f"subject_{period}", "Informe a matéria.")
            if teacher_id is None:
                self.add_error(f"teacher_{period}", "Informe o professor.")
            if subject_id is None or teacher_id is None:
                continue
            if lecture is None:
                lecture = Lecture(
                    school_class=self.school_class, date=self.date, period=period
                )
            elif (lecture.subject_id, lecture.teacher_id, lecture.topic) == (
                subject_id,
                teacher_id,
                topic,
            ):
                continue
            lecture.subject = self.subjects[subject_id]
            lecture.teacher = self.teachers[teacher_id]
            lecture.topic = topic
            try:
                lecture.full_clean()
            except ValidationError as error:
                for field, messages in error.message_dict.items():
                    row_field = f"{field}_{period}"
                    self.add_error(
                        row_field if row_field in self.fields else None, messages
                    )
                continue
            self.changed_lectures.append(lecture)
        return cleaned_data

    @transaction.atomic
    def save(self):
        for lecture in self.removed_lectures:
            lecture.delete()
        for lecture in self.changed_lectures:
            lecture.save()


class LectureForm(forms.ModelForm):
    """Edit one lecture; new lectures come from the day sheet."""

    class Meta:
        model = Lecture
        fields = ["school_class", "date", "period", "subject", "teacher", "topic"]
        widgets = {
            "school_class": forms.Select(
                attrs={"class": "select select-neutral w-full"}
            ),
            "date": date_input(),
            "period": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "subject": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "teacher": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "topic": forms.TextInput(attrs={"class": "input input-neutral w-full"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Kept in the form (disabled) so the unique (class, date, period) is checked.
        self.fields["school_class"].disabled = True
        grade_level = self.instance.school_class.grade_level
        self.fields["subject"].queryset = level_subjects(grade_level)
        self.fields["teacher"].queryset = level_teachers(grade_level)


class LectureFilterForm(forms.Form):
    school_year = forms.ModelChoiceField(
        label="Ano letivo",
        queryset=SchoolYear.objects.order_by("-begins"),
        required=False,
        empty_label="Todos",
        widget=forms.Select(attrs={"class": CELL}),
    )
    school_class = forms.ModelChoiceField(
        label="Turma",
        queryset=series_classes(),
        required=False,
        empty_label="Todas",
        widget=forms.Select(attrs={"class": CELL}),
    )
    subject = forms.ModelChoiceField(
        label="Matéria",
        queryset=Subject.objects.order_by("name"),
        required=False,
        empty_label="Todas",
        widget=forms.Select(attrs={"class": CELL}),
    )
    teacher = forms.ModelChoiceField(
        label="Professor",
        queryset=Employee.objects.order_by("name"),
        required=False,
        empty_label="Todos",
        widget=forms.Select(attrs={"class": CELL}),
    )
    date_from = forms.DateField(
        label="De",
        required=False,
        widget=date_input("input input-neutral input-sm w-full"),
    )
    date_to = forms.DateField(
        label="Até",
        required=False,
        widget=date_input("input input-neutral input-sm w-full"),
    )
