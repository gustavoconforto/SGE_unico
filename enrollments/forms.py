from django import forms
from django.forms import inlineformset_factory

from accounts.models import Account, Installment
from enrollments.models import (
    DiscountType,
    Enrollment,
    EnrollmentNeededDocument,
    EnrollmentType,
    NeededDocumentType,
    SchoolYear,
)


class SchoolYearForm(forms.ModelForm):
    class Meta:
        model = SchoolYear
        fields = [
            "begins",
            "ends",
            "bi_1_begins",
            "bi_1_ends",
            "bi_2_begins",
            "bi_2_ends",
            "bi_3_begins",
            "bi_3_ends",
            "bi_4_begins",
            "bi_4_ends",
        ]
        widgets = {
            "begins": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                    "class": "input input-neutral w-full",
                },
            ),
            "ends": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                    "class": "input input-neutral w-full",
                },
            ),
            "bi_1_begins": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                    "class": "input input-neutral w-full",
                },
            ),
            "bi_1_ends": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                    "class": "input input-neutral w-full",
                },
            ),
            "bi_2_begins": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                    "class": "input input-neutral w-full",
                },
            ),
            "bi_2_ends": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                    "class": "input input-neutral w-full",
                },
            ),
            "bi_3_begins": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                    "class": "input input-neutral w-full",
                },
            ),
            "bi_3_ends": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                    "class": "input input-neutral w-full",
                },
            ),
            "bi_4_begins": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                    "class": "input input-neutral w-full",
                },
            ),
            "bi_4_ends": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                    "class": "input input-neutral w-full",
                },
            ),
        }


class NeededDocumentTypeForm(forms.ModelForm):
    class Meta:
        model = NeededDocumentType
        fields = [
            "description",
        ]
        widgets = {
            "description": forms.TextInput(
                attrs={"class": "input input-neutral w-full"}
            )
        }


class DiscountTypeForm(forms.ModelForm):
    class Meta:
        model = DiscountType
        fields = ["description", "percentage"]
        widgets = {
            "description": forms.TextInput(
                attrs={"class": "input input-neutral w-full"}
            ),
            "percentage": forms.NumberInput(
                attrs={"class": "input input-neutral w-full"}
            ),
        }


class EnrollmentTypeForm(forms.ModelForm):
    class Meta:
        model = EnrollmentType
        fields = [
            "program",
            "level",
            "start_date",
            "end_date",
            "total_price",
            "description",
            "school_year",
        ]
        widgets = {
            "program": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "level": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "start_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                    "class": "input input-neutral w-full",
                },
            ),
            "end_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                    "class": "input input-neutral w-full",
                },
            ),
            "total_price": forms.NumberInput(
                attrs={"class": "input input-neutral w-full"}
            ),
            "description": forms.TextInput(
                attrs={"class": "input input-neutral w-full"}
            ),
            "school_year": forms.Select(
                attrs={"class": "select select-neutral w-full"}
            ),
        }


class EnrollmentForm(forms.ModelForm):
    # Filled automatically by the model; shown read-only. Using field.disabled
    # (instead of the HTML attribute) makes Django keep the stored value on
    # POST, since browsers don't submit disabled inputs.
    readonly_fields = [
        "enrolled_at",
        "gross_value",
        "discount_percent",
        "installments_count",
    ]

    class Meta:
        model = Enrollment
        fields = [
            "student",
            "enrollment_type",
            "school_class",
            "status",
            "enrolled_at",
            "discount",
            "gross_value",
            "discount_percent",
            "installments_count",
            "due_day",
        ]
        widgets = {
            "student": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "school_class": forms.Select(
                attrs={"class": "select select-neutral w-full"}
            ),
            "enrollment_type": forms.Select(
                attrs={"class": "select select-neutral w-full"}
            ),
            "discount": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "status": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "enrolled_at": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                    "class": "input input-neutral w-full",
                },
            ),
            "gross_value": forms.NumberInput(
                attrs={"class": "input input-neutral w-full"}
            ),
            "discount_percent": forms.NumberInput(
                attrs={"class": "input input-neutral w-full"}
            ),
            "installments_count": forms.NumberInput(
                attrs={"class": "input input-neutral w-full"}
            ),
            "due_day": forms.NumberInput(attrs={"class": "input input-neutral w-full"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.readonly_fields:
            self.fields[name].disabled = True


class EnrollmentNeededDocumentForm(forms.ModelForm):
    class Meta:
        model = EnrollmentNeededDocument
        fields = ["is_delivered"]
        widgets = {
            "is_delivered": forms.CheckboxInput(attrs={"class": "checkbox"}),
        }


# Documents are created by the post_save signal (one per NeededDocumentType),
# so the formset only edits existing rows: no extra blank form, type read-only.
EnrollmentNeededDocumentFormSet = inlineformset_factory(
    Enrollment,
    EnrollmentNeededDocument,
    form=EnrollmentNeededDocumentForm,
    extra=0,
    can_delete=False,
)


class InstallmentForm(forms.ModelForm):
    class Meta:
        model = Installment
        # status is derived from payments (Installment.refresh_status), so it's
        # displayed in the template rather than edited here.
        fields = ["due_date", "amount"]
        widgets = {
            "due_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date", "class": "input input-sm input-neutral"},
            ),
            "amount": forms.NumberInput(
                attrs={"class": "input input-sm input-neutral", "step": "0.01"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["due_date"].disabled = True


InstallmentFormSet = inlineformset_factory(
    Account,
    Installment,
    form=InstallmentForm,
    extra=0,
    can_delete=False,
)
