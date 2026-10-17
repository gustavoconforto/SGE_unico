from django import forms

from programs.models import Program


class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input input-neutral w-full"})
        }
