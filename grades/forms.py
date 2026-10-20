from django import forms

from grades.models import Subject


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = [
            "name",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input input-neutral w-full"}),
        }
