from django import forms

from incidents.models import Incident, IncidentType


class IncidentForm(forms.ModelForm):
    class Meta:
        model = Incident
        fields = ["incident_type", "student", "incident_data"]
        widgets = {
            "incident_type": forms.Select(
                attrs={"class": "select select-neutral w-full"}
            ),
            "student": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "incident_data": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date", "class": "input input-neutral w-full"},
            ),
        }


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
