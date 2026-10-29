from decimal import Decimal

from django import forms
from django.db.models import Count, Q
from django.forms import inlineformset_factory
from django.urls import reverse_lazy

from accounts.models import Account, Installment
from classes.models import Class
from enrollments.models import (
    DiscountGroup,
    DiscountType,
    Enrollment,
    EnrollmentDiscount,
    EnrollmentNeededDocument,
    EnrollmentStatus,
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
            "school_days",
            "total_hours",
        ]
        widgets = {
            "school_days": forms.NumberInput(
                attrs={"class": "input input-neutral w-full"}
            ),
            "total_hours": forms.NumberInput(
                attrs={"class": "input input-neutral w-full"}
            ),
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Nullable in the model only for years created before these fields.
        self.fields["school_days"].required = True
        self.fields["total_hours"].required = True


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
            "total_price",
            "punctuality_discount",
            "description",
            "school_year",
        ]
        widgets = {
            "program": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "level": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "total_price": forms.NumberInput(
                attrs={"class": "input input-neutral w-full"}
            ),
            "punctuality_discount": forms.NumberInput(
                attrs={"class": "input input-neutral w-full", "step": "0.01"}
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
        "first_discount_percent",
        "remaining_discount_percent",
    ]
    # The account and installments are generated from these on creation, so
    # they can't change afterwards.
    locked_on_edit_fields = ["student", "enrollment_type"]

    class Meta:
        model = Enrollment
        fields = [
            "student",
            "enrollment_type",
            "school_class",
            "status",
            "enrolled_at",
            "gross_value",
            "first_discount_percent",
            "remaining_discount_percent",
            "due_day",
        ]
        widgets = {
            "student": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "school_class": forms.Select(
                attrs={"class": "select select-neutral w-full"}
            ),
            "enrollment_type": forms.Select(
                attrs={
                    "class": "select select-neutral w-full",
                    "hx-get": reverse_lazy("enrollments:school_class_options"),
                    "hx-trigger": "change",
                    "hx-target": "#school-class-field",
                }
            ),
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
            "first_discount_percent": forms.NumberInput(
                attrs={"class": "input input-neutral w-full"}
            ),
            "remaining_discount_percent": forms.NumberInput(
                attrs={"class": "input input-neutral w-full"}
            ),
            "due_day": forms.NumberInput(attrs={"class": "input input-neutral w-full"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.readonly_fields:
            self.fields[name].disabled = True
        if self.instance.pk:
            for name in self.locked_on_edit_fields:
                self.fields[name].disabled = True
        self.fields["school_class"].queryset = self.school_classes_for(
            self.selected_enrollment_type()
        )
        self.fields["school_class"].label_from_instance = self.school_class_label

    def selected_enrollment_type(self):
        if self.instance.pk:
            return self.instance.enrollment_type
        if self.is_bound:
            pk = self.data.get(self.add_prefix("enrollment_type"))
        else:
            pk = self.initial.get("enrollment_type") or self.instance.enrollment_type_id
        pk = getattr(pk, "pk", pk)
        if not pk or not str(pk).isdigit():
            return None
        return EnrollmentType.objects.filter(pk=pk).first()

    @staticmethod
    def school_classes_for(enrollment_type):
        # Same rules as Enrollment.clean(): school year, program and grade.
        if enrollment_type is None:
            return Class.objects.none()
        classes = (
            Class.objects.select_related("year")
            .annotate(
                student_count=Count(
                    "enrollments",
                    filter=Q(enrollments__status=EnrollmentStatus.ACTIVE),
                )
            )
            .filter(
                year=enrollment_type.school_year_id,
                program=enrollment_type.program_id,
            )
        )
        if enrollment_type.level:
            classes = classes.filter(grade_level=int(enrollment_type.level))
        return classes

    @staticmethod
    def school_class_label(school_class):
        # e.g. "2° Inspiração - 2027 (12/50)": active students / capacity.
        capacity = school_class.capacity if school_class.capacity is not None else "—"
        return f"{school_class} ({school_class.student_count}/{capacity})"


# Form field prefix of each discount group: first_discount_types, ...
DISCOUNT_GROUP_PREFIXES = {
    DiscountGroup.FIRST: "first",
    DiscountGroup.REMAINING: "remaining",
}


class EnrollmentCreateForm(EnrollmentForm):
    """Adds the discounts, which only make sense on creation: the account is
    generated from them when the enrollment is first saved.

    Each group (first installment, remaining installments) has its own set
    of fields: discount types, custom percentage and its observation.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for prefix in DISCOUNT_GROUP_PREFIXES.values():
            self.fields[f"{prefix}_discount_types"] = forms.ModelMultipleChoiceField(
                label="Descontos",
                queryset=DiscountType.objects.all(),
                required=False,
                widget=forms.CheckboxSelectMultiple(
                    attrs={"class": "checkbox checkbox-sm checkbox-neutral"}
                ),
            )
            self.fields[f"{prefix}_discount_types"].label_from_instance = (
                lambda discount_type: f"{discount_type} ({discount_type.percentage}%)"
            )
            self.fields[f"{prefix}_custom_discount_percent"] = forms.DecimalField(
                label="Desconto avulso (%)",
                max_digits=5,
                decimal_places=2,
                min_value=Decimal("0.01"),
                max_value=Decimal(100),
                required=False,
                widget=forms.NumberInput(
                    attrs={"class": "input input-neutral w-full", "step": "0.01"}
                ),
            )
            self.fields[f"{prefix}_custom_discount_observation"] = forms.CharField(
                label="Observação do desconto avulso",
                max_length=200,
                required=False,
                help_text="Ex.: desconto autorizado pela direção",
                widget=forms.TextInput(attrs={"class": "input input-neutral w-full"}),
            )

    def clean(self):
        cleaned_data = super().clean()
        for group, prefix in DISCOUNT_GROUP_PREFIXES.items():
            percent = cleaned_data.get(f"{prefix}_custom_discount_percent")
            observation = cleaned_data.get(f"{prefix}_custom_discount_observation")
            if percent and not observation:
                self.add_error(
                    f"{prefix}_custom_discount_observation",
                    "Informe quem autorizou ou o motivo do desconto avulso.",
                )
            elif observation and not percent:
                self.add_error(
                    f"{prefix}_custom_discount_percent",
                    "Informe o percentual do desconto avulso.",
                )
            total = sum(d.percentage for d in self.build_discounts(group))
            if total > 100:
                self.add_error(
                    f"{prefix}_discount_types",
                    f"A soma dos descontos ({total}%) não pode passar de 100%.",
                )
        return cleaned_data

    def build_discounts(self, group):
        prefix = DISCOUNT_GROUP_PREFIXES[group]
        discounts = [
            EnrollmentDiscount(
                discount_type=discount_type,
                group=group,
                percentage=discount_type.percentage,
            )
            for discount_type in self.cleaned_data.get(f"{prefix}_discount_types") or []
        ]
        percent = self.cleaned_data.get(f"{prefix}_custom_discount_percent")
        if percent:
            discounts.append(
                EnrollmentDiscount(
                    group=group,
                    percentage=percent,
                    observation=self.cleaned_data.get(
                        f"{prefix}_custom_discount_observation"
                    ),
                )
            )
        return discounts

    def save(self, commit=True):
        self.instance.save_with_discounts(
            [
                discount
                for group in DISCOUNT_GROUP_PREFIXES
                for discount in self.build_discounts(group)
            ]
        )
        return self.instance


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
    exclude=["amount"],
)
