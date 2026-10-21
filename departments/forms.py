from django import forms

from departments.models import Department


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "teachers"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input input-neutral w-full"}),
            "teachers": forms.CheckboxSelectMultiple(
                attrs={"class": "checkbox checkbox-sm checkbox-neutral"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["teachers"].queryset = self.fields["teachers"].queryset.order_by(
            "name"
        )
