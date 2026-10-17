from django import forms

from classes.models import Class


class ClassForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = ["program", "year", "grade_level", "name", "capacity"]
        widgets = {
            "program": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "year": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "grade_level": forms.NumberInput(
                attrs={"class": "input input-neutral w-full"}
            ),
            "name": forms.TextInput(attrs={"class": "input input-neutral w-full"}),
            "capacity": forms.NumberInput(
                attrs={"class": "input input-neutral w-full"}
            ),
        }
