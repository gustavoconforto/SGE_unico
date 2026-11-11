from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from accounts.forms import date_input
from employees.models import Employee
from enrollments.models import Enrollment, EnrollmentStatus, SchoolYear
from grades.models import Bimester
from incidents.forms import ActiveEnrollmentFormMixin
from incidents.services import bimester_range
from lessons.models import Weekday
from pathways.models import (
    AttendanceStatus,
    Pathway,
    PathwayAttendance,
    PathwayEnrollment,
    PathwayGrade,
    PathwayOffering,
    PathwaySession,
)
from pathways.services import attendance_rate, with_attendance


def offerings():
    return PathwayOffering.objects.select_related("pathway", "school_year")


def offering_select(css="select select-neutral w-full"):
    return forms.Select(attrs={"class": css})


# PATHWAY FORMS


class PathwayForm(forms.ModelForm):
    class Meta:
        model = Pathway
        fields = ["name", "extra_points", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input input-neutral w-full"}),
            "extra_points": forms.NumberInput(
                attrs={"class": "input input-neutral w-full", "min": 0, "step": "0.01"}
            ),
            "description": forms.Textarea(
                attrs={"class": "textarea textarea-neutral w-full", "rows": 3}
            ),
        }


# PATHWAY OFFERING FORMS


class PathwayOfferingForm(forms.ModelForm):
    weekdays = forms.TypedMultipleChoiceField(
        label="Dias de aula",
        required=False,
        coerce=int,
        choices=Weekday.choices,
        help_text="Dias da semana em que há aula; montam as datas do diário",
        widget=forms.CheckboxSelectMultiple(
            attrs={"class": "checkbox checkbox-sm checkbox-neutral"}
        ),
    )

    class Meta:
        model = PathwayOffering
        fields = [
            "pathway",
            "school_year",
            "name",
            "schedule",
            "capacity",
            "weekdays",
            "teachers",
        ]
        widgets = {
            "pathway": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "school_year": forms.Select(
                attrs={"class": "select select-neutral w-full"}
            ),
            "name": forms.TextInput(attrs={"class": "input input-neutral w-full"}),
            "schedule": forms.TextInput(attrs={"class": "input input-neutral w-full"}),
            "capacity": forms.NumberInput(
                attrs={"class": "input input-neutral w-full", "min": 1}
            ),
            "teachers": forms.CheckboxSelectMultiple(
                attrs={"class": "checkbox checkbox-sm checkbox-neutral"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["school_year"].queryset = SchoolYear.objects.order_by("-begins")
        self.fields["teachers"].queryset = Employee.objects.order_by("name")

    def clean_capacity(self):
        capacity = self.cleaned_data["capacity"]
        if capacity is not None and capacity < 1:
            raise forms.ValidationError("Informe ao menos uma vaga.")
        return capacity


class PathwayOfferingFilterForm(forms.Form):
    school_year = forms.ModelChoiceField(
        label="Ano escolar",
        queryset=SchoolYear.objects.order_by("-begins"),
        required=False,
        empty_label="Todos",
        widget=forms.Select(attrs={"class": "select select-neutral select-sm w-full"}),
    )
    pathway = forms.ModelChoiceField(
        label="Itinerário",
        queryset=Pathway.objects.all(),
        required=False,
        empty_label="Todos",
        widget=forms.Select(attrs={"class": "select select-neutral select-sm w-full"}),
    )


class OfferingFilterForm(forms.Form):
    offering = forms.ModelChoiceField(
        label="Turma de itinerário",
        queryset=offerings(),
        required=False,
        empty_label="Todas",
        widget=offering_select("select select-neutral select-sm w-full"),
    )


# PATHWAY ENROLLMENT FORMS


class PathwayEnrollmentForm(ActiveEnrollmentFormMixin, forms.ModelForm):
    class Meta:
        model = PathwayEnrollment
        fields = ["offering", "enrollment", "joined_at", "left_at"]
        widgets = {
            "offering": offering_select(),
            "enrollment": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "joined_at": date_input(),
            "left_at": date_input(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["offering"].queryset = offerings()
        # With the offering known (prefilled or edited), list only the
        # enrollments of its school year.
        offering_id = self.instance.offering_id or self.initial.get("offering")
        offering = offerings().filter(pk=offering_id).first() if offering_id else None
        if offering:
            enrollment = self.fields["enrollment"]
            enrollment.queryset = enrollment.queryset.filter(
                enrollment_type__school_year=offering.school_year_id
            )


class PathwayEnrollmentFilterForm(OfferingFilterForm):
    status = forms.ChoiceField(
        label="Situação",
        required=False,
        choices=[("", "Todas"), ("current", "Inscritos"), ("left", "Saíram")],
        widget=forms.Select(attrs={"class": "select select-neutral select-sm w-full"}),
    )


class StudentPathwaysSelectForm(forms.Form):
    enrollment = forms.ModelChoiceField(
        label="Matrícula",
        required=False,
        queryset=Enrollment.objects.filter(status=EnrollmentStatus.ACTIVE)
        .select_related("student", "enrollment_type__program")
        .select_related("enrollment_type__school_year")
        .order_by("student__name"),
        empty_label="Selecione um aluno",
        widget=forms.Select(attrs={"class": "select select-neutral w-full"}),
    )


class StudentPathwaysForm(forms.Form):
    """Every pathway offering of an enrollment's school year, ticked when the
    student is in it. Unticking sets the leaving date; ticking again reopens
    the pathway enrollment."""

    def __init__(self, *args, enrollment, **kwargs):
        super().__init__(*args, **kwargs)
        self.enrollment = enrollment
        self.offerings = list(
            offerings()
            .filter(school_year=enrollment.enrollment_type.school_year_id)
            .annotate(
                taken=Count(
                    "pathway_enrollments",
                    filter=Q(pathway_enrollments__left_at__isnull=True),
                )
            )
            .order_by("pathway__name", "name")
        )
        self.existing = {
            member.offering_id: member
            for member in enrollment.pathway_enrollments.all()
        }
        for offering in self.offerings:
            current = self.is_current(offering)
            full = offering.capacity is not None and offering.taken >= offering.capacity
            self.fields[self.field_name(offering)] = forms.BooleanField(
                label=str(offering),
                required=False,
                initial=current,
                disabled=full and not current,
                widget=forms.CheckboxInput(
                    attrs={"class": "checkbox checkbox-sm checkbox-neutral"}
                ),
            )

    @staticmethod
    def field_name(offering):
        return f"offering_{offering.pk}"

    def is_current(self, offering):
        member = self.existing.get(offering.pk)
        return member is not None and member.left_at is None

    def rows(self):
        """(offering, bound field, pathway enrollment or None)."""
        for offering in self.offerings:
            yield (
                offering,
                self[self.field_name(offering)],
                self.existing.get(offering.pk),
            )

    def clean(self):
        cleaned_data = super().clean()
        self.changes = []
        today = timezone.localdate()
        for offering in self.offerings:
            name = self.field_name(offering)
            if cleaned_data.get(name) == self.is_current(offering):
                continue
            member = self.existing.get(offering.pk)
            if member is None:
                member = PathwayEnrollment(
                    enrollment=self.enrollment, offering=offering, joined_at=today
                )
            elif member.left_at is None:
                member.left_at = max(today, member.joined_at)
            else:
                member.left_at = None
            try:
                member.full_clean()
            except ValidationError as error:
                self.add_error(name, error.messages)
            else:
                self.changes.append(member)
        return cleaned_data

    @transaction.atomic
    def save(self):
        today = timezone.localdate()
        for member in self.changes:
            # A pathway the student hasn't started, with nothing recorded, is
            # dropped instead of getting a leaving date.
            if (
                member.left_at
                and member.joined_at > today
                and not member.attendances.exists()
                and not member.grades.exists()
            ):
                member.delete()
            else:
                member.save()


# PATHWAY SESSION FORMS


class PathwaySessionForm(forms.ModelForm):
    class Meta:
        model = PathwaySession
        fields = ["offering", "date", "topic"]
        widgets = {
            "offering": offering_select(),
            "date": date_input(),
            "topic": forms.TextInput(attrs={"class": "input input-neutral w-full"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["offering"].queryset = offerings()
        if self.instance.pk:
            # The roll call belongs to the offering's students.
            self.fields["offering"].disabled = True

    @transaction.atomic
    def save(self, commit=True):
        session = super().save(commit)
        if commit and "date" in self.changed_data:
            # Students who weren't in the pathway on the new date leave the roll call.
            session.attendances.exclude(
                pathway_enrollment__in=members_on(session.offering, session.date)
            ).delete()
        return session


class PathwaySessionFilterForm(OfferingFilterForm):
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


def members_on(offering, day):
    """The offering's pathway enrollments on `day`."""
    return (
        offering.pathway_enrollments.filter(joined_at__lte=day)
        .filter(Q(left_at__isnull=True) | Q(left_at__gte=day))
        .select_related("enrollment__student")
        .order_by("enrollment__student__name")
    )


def members_between(offering, begins, ends):
    """The offering's pathway enrollments at some point between the dates."""
    return (
        offering.pathway_enrollments.filter(joined_at__lte=ends)
        .filter(Q(left_at__isnull=True) | Q(left_at__gte=begins))
        .select_related("enrollment__student")
        .order_by("enrollment__student__name")
    )


class AttendanceSheetForm(forms.Form):
    """The roll call of a lesson: one status per student in the pathway on its
    date, present unless recorded otherwise."""

    def __init__(self, *args, session, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session
        self.members = list(members_on(session.offering, session.date))
        self.existing = {
            attendance.pathway_enrollment_id: attendance
            for attendance in session.attendances.all()
        }
        for member in self.members:
            attendance = self.existing.get(member.pk)
            self.fields[self.field_name(member)] = forms.ChoiceField(
                label=str(member.enrollment.student),
                choices=AttendanceStatus.choices,
                initial=attendance.status if attendance else AttendanceStatus.PRESENT,
                widget=forms.Select(
                    attrs={"class": "select select-neutral select-sm w-48"}
                ),
            )

    @staticmethod
    def field_name(member):
        return f"status_{member.pk}"

    def rows(self):
        for member in self.members:
            yield member, self[self.field_name(member)]

    @transaction.atomic
    def save(self):
        for member in self.members:
            status = self.cleaned_data[self.field_name(member)]
            attendance = self.existing.get(member.pk)
            if attendance is None:
                PathwayAttendance.objects.create(
                    session=self.session, pathway_enrollment=member, status=status
                )
            elif attendance.status != status:
                attendance.status = status
                attendance.save(update_fields=["status"])


# PATHWAY GRADE FORMS


class PathwayGradeSelectForm(forms.Form):
    """Pick an offering and a bimester to enter its pathway grades; only
    pathways that give an extra grade are listed."""

    offering = forms.ModelChoiceField(
        label="Turma de itinerário",
        required=False,
        queryset=offerings().filter(pathway__extra_points__gt=0),
        empty_label="Selecione uma turma de itinerário",
        widget=offering_select(),
    )
    bimester = forms.TypedChoiceField(
        label="Bimestre",
        required=False,
        coerce=int,
        empty_value=None,
        choices=[("", "Selecione um bimestre"), *Bimester.choices],
        widget=forms.Select(attrs={"class": "select select-neutral w-full"}),
    )


class PathwayGradeSheetForm(forms.Form):
    """Every pathway grade of an offering in a bimester: a row per student in
    the pathway during the bimester, up to the pathway's `extra_points`.
    Blank cells delete the grade."""

    def __init__(self, *args, offering, bimester, **kwargs):
        super().__init__(*args, **kwargs)
        self.offering = offering
        self.bimester = bimester
        date_range = bimester_range(offering.school_year, bimester)
        self.has_dates = date_range is not None
        self.max_score = offering.pathway.extra_points
        self.members = list(
            with_attendance(members_between(offering, *date_range), date_range)
            if date_range
            else offering.pathway_enrollments.select_related(
                "enrollment__student"
            ).order_by("enrollment__student__name")
        )
        self.existing = {
            grade.pathway_enrollment_id: grade
            for grade in PathwayGrade.objects.filter(
                pathway_enrollment__in=self.members, bimester=bimester
            )
        }
        for member in self.members:
            grade = self.existing.get(member.pk)
            self.fields[self.field_name(member)] = forms.DecimalField(
                label=str(member.enrollment.student),
                required=False,
                min_value=0,
                max_value=self.max_score,
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

    @staticmethod
    def field_name(member):
        return f"score_{member.pk}"

    def rows(self):
        """(pathway enrollment, bound field, attendance rate); the rate is
        None without bimester dates or lessons."""
        for member in self.members:
            rate = (
                attendance_rate(member.present, member.absent)
                if self.has_dates
                else None
            )
            yield member, self[self.field_name(member)], rate

    @transaction.atomic
    def save(self):
        for member in self.members:
            score = self.cleaned_data[self.field_name(member)]
            grade = self.existing.get(member.pk)
            if score is None:
                if grade:
                    grade.delete()
            elif grade is None:
                PathwayGrade.objects.create(
                    pathway_enrollment=member, bimester=self.bimester, score=score
                )
            elif grade.score != score:
                grade.score = score
                grade.save(update_fields=["score", "updated_at"])
