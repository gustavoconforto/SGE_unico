from django import forms
from django.db.models import Q

from accounts.forms import date_input
from enrollments.models import Enrollment, EnrollmentStatus
from grades.models import Bimester
from incidents.models import BathroomPermission, Incident, IncidentType, StudentDelay


class ActiveEnrollmentFormMixin:
    """Limit the enrollment select to active enrollments, keeping the current
    one when editing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["enrollment"].queryset = Enrollment.objects.filter(
            Q(status=EnrollmentStatus.ACTIVE) | Q(pk=self.instance.enrollment_id)
        ).select_related(
            "student", "enrollment_type__program", "enrollment_type__school_year"
        )


class IncidentForm(ActiveEnrollmentFormMixin, forms.ModelForm):
    class Meta:
        model = Incident
        fields = ["incident_type", "enrollment", "incident_date"]
        widgets = {
            "incident_type": forms.Select(
                attrs={"class": "select select-neutral w-full"}
            ),
            "enrollment": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "incident_date": date_input(),
        }


class StudentDelayForm(ActiveEnrollmentFormMixin, forms.ModelForm):
    class Meta:
        model = StudentDelay
        fields = ["enrollment", "delay_type", "incident_date"]
        widgets = {
            "enrollment": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "delay_type": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "incident_date": date_input(),
        }


class BathroomPermissionForm(ActiveEnrollmentFormMixin, forms.ModelForm):
    class Meta:
        model = BathroomPermission
        fields = ["enrollment", "class_period", "incident_date"]
        widgets = {
            "enrollment": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "class_period": forms.NumberInput(
                attrs={"class": "input input-neutral w-full", "min": 1}
            ),
            "incident_date": date_input(),
        }

    def clean_class_period(self):
        class_period = self.cleaned_data["class_period"]
        if class_period is not None and class_period < 1:
            raise forms.ValidationError("O horário deve ser maior que zero.")
        return class_period


class IncidentTypeForm(forms.ModelForm):
    class Meta:
        model = IncidentType
        fields = [
            "type",
            "penalty",
        ]
        widgets = {
            "type": forms.TextInput(attrs={"class": "input input-neutral w-full"}),
            "penalty": forms.NumberInput(
                attrs={"class": "input input-neutral w-full", "min": 0, "step": "0.1"}
            ),
        }

    def clean_penalty(self):
        penalty = self.cleaned_data["penalty"]
        if penalty is not None and penalty < 0:
            raise forms.ValidationError("A penalidade não pode ser negativa.")
        return penalty


def active_enrollments():
    return (
        Enrollment.objects.filter(status=EnrollmentStatus.ACTIVE)
        .select_related(
            "student",
            "school_class",
            "enrollment_type__program",
            "enrollment_type__school_year",
        )
        .order_by("student__name")
    )


class ConceptGradeForm(forms.Form):
    """Pick an active enrollment and a bimester to compute its concept grade."""

    enrollment = forms.ModelChoiceField(
        label="Aluno",
        required=False,
        queryset=Enrollment.objects.none(),
        empty_label="Selecione um aluno",
        widget=forms.Select(attrs={"class": "select select-neutral w-full"}),
    )
    bimester = forms.TypedChoiceField(
        label="Bimestre",
        required=False,
        coerce=int,
        empty_value=None,
        choices=[("", "Selecione um bimestre"), *Bimester.choices],
        widget=forms.Select(attrs={"class": "select select-neutral w-full"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["enrollment"].queryset = active_enrollments()


class ConceptBimesterFilterForm(forms.Form):
    bimester = forms.TypedChoiceField(
        label="Bimestre",
        required=False,
        coerce=int,
        empty_value=None,
        choices=[("", "Selecione um bimestre"), *Bimester.choices],
        widget=forms.Select(attrs={"class": "select select-neutral select-sm w-full"}),
    )
