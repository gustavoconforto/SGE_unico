from django import forms
from django.forms.models import inlineformset_factory

from students.models import Guardian, GuardianAssociation, Student


class GuardianForm(forms.ModelForm):
    TABS = {
        "personal": [
            "name",
            "sex",
            "cpf",
            "rg",
            "issuing_authority",
            "birth_date",
            "nationality",
            "place_of_birth",
            "marital_status",
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
        model = Guardian
        fields = [
            "name",
            "sex",
            "cpf",
            "rg",
            "marital_status",
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
            "marital_status": forms.Select(
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
        }


class StudentForm(forms.ModelForm):
    TABS = {
        "personal": [
            "name",
            "use_social_name",
            "social_name",
            "registration",
            "photo",
            "sex",
            "cpf",
            "rg",
            "issuing_authority",
            "birth_date",
            "nationality",
            "place_of_birth",
            "marital_status",
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
        model = Student
        fields = [
            "name",
            "use_social_name",
            "social_name",
            "registration",
            "photo",
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
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "placeholder": "Digite...",
                }
            ),
            "use_social_name": forms.CheckboxInput(attrs={"class": "toggle"}),
            "photo": forms.FileInput(
                attrs={
                    "class": "file-input file-input-neutral w-full",
                    "accept": "image/*",
                }
            ),
            "social_name": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "placeholder": "Digite...",
                }
            ),
            "registration": forms.NumberInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "placeholder": "Digite...",
                    "disabled": True,
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
            "marital_status": forms.Select(
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
        }


class GuardianAssociationForm(forms.ModelForm):
    class Meta:
        model = GuardianAssociation
        fields = [
            "guardian",
            "relationship",
            "is_financial",
            "is_primary_contact",
            "living_with",
            "pick_up",
        ]
        widgets = {
            "guardian": forms.Select(
                attrs={
                    "class": "select select-neutral w-full",
                }
            ),
            "relationship": forms.Select(
                attrs={
                    "class": "select select-neutral w-full",
                }
            ),
            "is_financial": forms.CheckboxInput(attrs={"class": "toggle"}),
            "is_primary_contact": forms.CheckboxInput(attrs={"class": "toggle"}),
            "living_with": forms.CheckboxInput(attrs={"class": "toggle"}),
            "pick_up": forms.CheckboxInput(attrs={"class": "toggle"}),
        }


GuardianFormSet = inlineformset_factory(
    Student,
    GuardianAssociation,
    form=GuardianAssociationForm,
    extra=1,
    can_delete=True,
)
