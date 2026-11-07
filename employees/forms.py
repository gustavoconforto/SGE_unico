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
                }
            ),
            "rg": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                }
            ),
            "cpf": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                }
            ),
            "issuing_authority": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
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
                }
            ),
            "place_of_birth": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                }
            ),
            "mobile": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "input input-neutral w-full",
                }
            ),
            "address": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                }
            ),
            "neighborhood": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                }
            ),
            "city": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                }
            ),
            "state": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                }
            ),
            "zip_code": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                }
            ),
            "role": forms.Select(
                attrs={
                    "class": "select select-neutral  w-full",
                }
            ),
        }
