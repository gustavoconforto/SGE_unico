from django import forms
from django.db.models import Q

from accounts.forms import date_input
from grades.models import Subject
from incidents.forms import ActiveEnrollmentFormMixin, current_school_year
from q_and_a.models import QandA


class QandAForm(ActiveEnrollmentFormMixin, forms.ModelForm):
    class Meta:
        model = QandA
        fields = ["enrollment", "subject", "q_and_a_date"]
        widgets = {
            "enrollment": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "subject": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "q_and_a_date": date_input(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A student may have enrollments in several years; offer only the
        # current one, keeping the saved enrollment when editing.
        self.fields["enrollment"].queryset = self.fields["enrollment"].queryset.filter(
            Q(enrollment_type__school_year=current_school_year())
            | Q(pk=self.instance.enrollment_id)
        )


class QandAFilterForm(forms.Form):
    subject = forms.ModelChoiceField(
        label="Disciplina",
        queryset=Subject.objects.all(),
        required=False,
        empty_label="Todas",
        widget=forms.Select(attrs={"class": "select select-neutral select-sm w-full"}),
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
