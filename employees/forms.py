from django import forms

from employees.models import Employee, EmployeeRoleType


class EmployeeRoleTypeForm(forms.ModelForm):
    class Meta:
        model = EmployeeRoleType
        fields = ["role"]
        widgets = {
            "role": forms.TextInput(attrs={"class": "input input-neutral w-full"})
        }


class EmployeeForm(forms.ModelForm):
    TABS = {
        "personal": [
            "name",
            "sex",
            "role",
            "cpf",
            "rg",
            "issuing_authority",
            "birth_date",
            "nationality",
            "place_of_birth",
        ],
        "contact": ["phone", "mobile", "email"],
        "address": ["address", "neighborhood", "city", "state", "zip_code"],
    }

    @property
    def active_tab(self):
        for tab, fields in self.TABS.items():
            if any(field in self.errors for field in fields):
                return tab
        return "personal"

    class Meta:
        model = Employee
        fields = [
            "name",
            "sex",
            "cpf",
            "rg",
            "issuing_authority",
            "birth_date",
            "nationality",
            "place_of_birth",
            "phone",
            "mobile",
            "email",
            "address",
            "neighborhood",
            "city",
            "state",
            "zip_code",
            "role",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "placeholder": "Digite...",
                }
            ),
            "rg": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "placeholder": "Digite...",
                }
            ),
            "cpf": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "placeholder": "Digite...",
                }
            ),
            "issuing_authority": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "placeholder": "Digite...",
                }
            ),
            "sex": forms.Select(
                attrs={
                    "class": "select select-neutral w-full",
                }
            ),
            "birth_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                    "class": "input input-neutral w-full",
                },
            ),
            "nationality": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "placeholder": "Digite...",
                }
            ),
            "place_of_birth": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "placeholder": "Digite...",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "placeholder": "Digite...",
                }
            ),
            "mobile": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "placeholder": "Digite...",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "placeholder": "Digite...",
                }
            ),
            "address": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "placeholder": "Digite...",
                }
            ),
            "neighborhood": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "placeholder": "Digite...",
                }
            ),
            "city": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "placeholder": "Digite...",
                }
            ),
            "state": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "placeholder": "Digite...",
                }
            ),
            "zip_code": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "placeholder": "Digite...",
                }
            ),
            "role": forms.Select(
                attrs={
                    "class": "select select-neutral  w-full",
                }
            ),
        }
