import re

from django import forms
from django.forms.models import BaseInlineFormSet, inlineformset_factory

from students.models import Guardian, GuardianAssociation, Student


class PhoneDigitsMixin:
    """Stores phone and mobile as digits only (DDD + number); the screen masks them."""

    def _phone_digits(self, field):
        digits = re.sub(r"\D", "", self.cleaned_data.get(field) or "")
        if digits and len(digits) not in (10, 11):
            raise forms.ValidationError("Informe DDD + número (10 ou 11 dígitos).")
        return digits

    def clean_phone(self):
        return self._phone_digits("phone")

    def clean_mobile(self):
        return self._phone_digits("mobile")


class GuardianForm(PhoneDigitsMixin, forms.ModelForm):
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
                    "inputmode": "tel",
                    "data-mask": "phone",
                }
            ),
            "mobile": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "inputmode": "tel",
                    "data-mask": "phone",
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
        }


class StudentForm(PhoneDigitsMixin, forms.ModelForm):
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
            "is_self_financial",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                }
            ),
            "use_social_name": forms.CheckboxInput(attrs={"class": "toggle"}),
            "is_self_financial": forms.CheckboxInput(attrs={"class": "toggle"}),
            "photo": forms.FileInput(
                attrs={
                    "class": "file-input file-input-neutral w-full",
                    "accept": "image/*",
                }
            ),
            "social_name": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                }
            ),
            "registration": forms.NumberInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "disabled": True,
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
                    "inputmode": "tel",
                    "data-mask": "phone",
                }
            ),
            "mobile": forms.TextInput(
                attrs={
                    "class": "input input-neutral w-full",
                    "inputmode": "tel",
                    "data-mask": "phone",
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
                    "data-searchable": "",
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


class BaseGuardianFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        financial = sum(
            1
            for form in self.forms
            if form.cleaned_data.get("is_financial")
            and not form.cleaned_data.get("DELETE")
        )
        if financial > 1:
            raise forms.ValidationError(
                "Apenas um responsável pode ser o responsável financeiro."
            )
        # The student form is posted with the formset, unprefixed.
        self_financial = bool(self.data.get("is_self_financial"))
        if financial and self_financial:
            raise forms.ValidationError(
                "O aluno é o próprio responsável financeiro; desmarque o "
                "responsável financeiro na lista ou desmarque essa opção."
            )
        if not financial and not self_financial:
            raise forms.ValidationError(
                "Marque um responsável financeiro ou indique que o próprio aluno "
                "é o responsável financeiro."
            )


GuardianFormSet = inlineformset_factory(
    Student,
    GuardianAssociation,
    form=GuardianAssociationForm,
    formset=BaseGuardianFormSet,
    extra=1,
    can_delete=True,
)
