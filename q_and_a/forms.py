from django import forms

from accounts.forms import date_input
from grades.models import Subject
from incidents.forms import ActiveEnrollmentFormMixin
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
