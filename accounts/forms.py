from django import forms
from django.db.models import Max
from django.utils import timezone

from accounts.models import (
    ZERO,
    Account,
    AccountType,
    Direction,
    Installment,
    InstallmentStatus,
    Payment,
    PaymentMethod,
    Supplier,
)


def date_input(css="input input-neutral w-full"):
    return forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "class": css})


# SUPPLIER FORMS


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "document", "phone", "email", "notes"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input input-neutral w-full"}),
            "document": forms.TextInput(
                attrs={"class": "input input-neutral w-full", "inputmode": "numeric"}
            ),
            "phone": forms.TextInput(attrs={"class": "input input-neutral w-full"}),
            "email": forms.EmailInput(attrs={"class": "input input-neutral w-full"}),
            "notes": forms.Textarea(
                attrs={"class": "textarea textarea-neutral w-full", "rows": 3}
            ),
        }

    def clean_document(self):
        document = self.cleaned_data["document"]
        if document and not document.isdigit():
            raise forms.ValidationError("Informe somente números.")
        if document and len(document) not in (11, 14):
            raise forms.ValidationError("O CPF deve ter 11 dígitos e o CNPJ, 14.")
        return document


# ACCOUNT TYPE FORMS


class AccountTypeForm(forms.ModelForm):
    class Meta:
        model = AccountType
        fields = ["name", "direction"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input input-neutral w-full"}),
            "direction": forms.Select(attrs={"class": "select select-neutral w-full"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Accounts only accept categories of their own direction, so it
        # can't change once the category is in use.
        if self.instance.pk and self.instance.accounts.exists():
            self.fields["direction"].disabled = True
            self.fields["direction"].help_text = (
                "Não pode ser alterada: a categoria já possui contas."
            )


class AccountTypeFilterForm(forms.Form):
    direction = forms.ChoiceField(
        label="Natureza",
        choices=[("", "Todas")] + Direction.choices,
        required=False,
        widget=forms.Select(attrs={"class": "select select-neutral select-sm w-full"}),
    )


# ACCOUNT FORMS


class AccountForm(forms.ModelForm):
    """Base form; subclasses set `direction` and the counterpart field."""

    direction = None
    # Values are split into installments on creation, so they are locked
    # afterwards to keep the installments consistent with the account.
    locked_on_edit = ["gross_value", "discount_value"]

    installments_count = forms.IntegerField(
        label="Número de parcelas",
        min_value=1,
        max_value=120,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "input input-neutral w-full"}),
    )
    first_due_date = forms.DateField(
        label="Primeiro vencimento",
        initial=timezone.localdate,
        widget=date_input(),
    )

    class Meta:
        model = Account
        fields = [
            "description",
            "category",
            "issue_date",
            "gross_value",
            "discount_value",
            "notes",
        ]
        widgets = {
            "description": forms.TextInput(
                attrs={"class": "input input-neutral w-full"}
            ),
            "category": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "issue_date": date_input(),
            "gross_value": forms.NumberInput(
                attrs={"class": "input input-neutral w-full", "step": "0.01"}
            ),
            "discount_value": forms.NumberInput(
                attrs={"class": "input input-neutral w-full", "step": "0.01"}
            ),
            "notes": forms.Textarea(
                attrs={"class": "textarea textarea-neutral w-full", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.direction = self.direction
        self.fields["category"].queryset = AccountType.objects.filter(
            direction=self.direction
        )
        if self.instance.pk:
            del self.fields["installments_count"]
            del self.fields["first_due_date"]
            for name in self.locked_on_edit:
                self.fields[name].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        gross = cleaned_data.get("gross_value")
        discount = cleaned_data.get("discount_value") or ZERO
        if gross is not None and discount > gross:
            self.add_error("discount_value", "O desconto não pode exceder o valor bruto.")
        return cleaned_data


class AccountReceivableForm(AccountForm):
    direction = Direction.RECEIVABLE

    class Meta(AccountForm.Meta):
        fields = AccountForm.Meta.fields + ["guardian"]
        widgets = AccountForm.Meta.widgets | {
            "guardian": forms.Select(attrs={"class": "select select-neutral w-full"}),
        }


class AccountPayableForm(AccountForm):
    direction = Direction.PAYABLE

    class Meta(AccountForm.Meta):
        fields = AccountForm.Meta.fields + ["supplier"]
        widgets = AccountForm.Meta.widgets | {
            "supplier": forms.Select(attrs={"class": "select select-neutral w-full"}),
        }


class AccountStatus:
    PENDING = "pending"
    OVERDUE = "overdue"
    PAID = "paid"
    CANCELLED = "cancelled"

    choices = [
        ("", "Todas"),
        (PENDING, "Em aberto"),
        (OVERDUE, "Vencidas"),
        (PAID, "Quitadas"),
        (CANCELLED, "Canceladas"),
    ]


class AccountFilterForm(forms.Form):
    direction = None

    category = forms.ModelChoiceField(
        label="Categoria",
        queryset=AccountType.objects.none(),
        required=False,
        empty_label="Todas",
        widget=forms.Select(attrs={"class": "select select-neutral select-sm w-full"}),
    )
    status = forms.ChoiceField(
        label="Situação",
        choices=AccountStatus.choices,
        required=False,
        widget=forms.Select(attrs={"class": "select select-neutral select-sm w-full"}),
    )
    issue_from = forms.DateField(
        label="Emitida a partir de",
        required=False,
        widget=date_input("input input-neutral input-sm w-full"),
    )
    issue_to = forms.DateField(
        label="Emitida até",
        required=False,
        widget=date_input("input input-neutral input-sm w-full"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = AccountType.objects.filter(
            direction=self.direction
        )


class AccountReceivableFilterForm(AccountFilterForm):
    direction = Direction.RECEIVABLE


class AccountPayableFilterForm(AccountFilterForm):
    direction = Direction.PAYABLE


# INSTALLMENT FORMS


class AccountChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        counterpart = f" - {obj.counterpart}" if obj.counterpart else ""
        return f"[{obj.get_direction_display()}] {obj}{counterpart}"


class InstallmentForm(forms.ModelForm):
    account = AccountChoiceField(
        label="Conta",
        queryset=Account.objects.select_related("guardian", "supplier"),
        widget=forms.Select(attrs={"class": "select select-neutral w-full"}),
    )

    class Meta:
        model = Installment
        fields = ["account", "number", "due_date", "amount"]
        widgets = {
            "number": forms.NumberInput(
                attrs={"class": "input input-neutral w-full", "min": 1}
            ),
            "due_date": date_input(),
            "amount": forms.NumberInput(
                attrs={"class": "input input-neutral w-full", "step": "0.01"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["number"].required = False
        self.fields["number"].help_text = "Deixe em branco para usar o próximo número"

    def clean(self):
        cleaned_data = super().clean()
        account = cleaned_data.get("account")
        if account and not cleaned_data.get("number"):
            last = account.installments.aggregate(last=Max("number"))["last"]
            cleaned_data["number"] = (last or 0) + 1
        return cleaned_data


class InstallmentFilterStatus:
    PENDING = "pending"
    OVERDUE = "overdue"

    choices = [
        ("", "Todas"),
        (PENDING, "Pendentes"),
        (OVERDUE, "Vencidas"),
    ] + InstallmentStatus.choices


class InstallmentFilterForm(forms.Form):
    direction = forms.ChoiceField(
        label="Natureza",
        choices=[("", "Todas")] + Direction.choices,
        required=False,
        widget=forms.Select(attrs={"class": "select select-neutral select-sm w-full"}),
    )
    status = forms.ChoiceField(
        label="Situação",
        choices=InstallmentFilterStatus.choices,
        required=False,
        widget=forms.Select(attrs={"class": "select select-neutral select-sm w-full"}),
    )
    due_from = forms.DateField(
        label="Vencimento a partir de",
        required=False,
        widget=date_input("input input-neutral input-sm w-full"),
    )
    due_to = forms.DateField(
        label="Vencimento até",
        required=False,
        widget=date_input("input input-neutral input-sm w-full"),
    )


# PAYMENT FORMS


class InstallmentChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return (
            f"{obj.account} - {obj.number}ª parcela - "
            f"venc. {obj.due_date:%d/%m/%Y} - R$ {obj.amount}"
        )


class PaymentForm(forms.ModelForm):
    installment = InstallmentChoiceField(
        label="Parcela",
        queryset=Installment.objects.none(),
        widget=forms.Select(attrs={"class": "select select-neutral w-full"}),
    )

    class Meta:
        model = Payment
        fields = [
            "installment",
            "paid_at",
            "amount",
            "penalty",
            "interest",
            "monetary_adjust",
            "method",
            "notes",
        ]
        widgets = {
            "paid_at": date_input(),
            "amount": forms.NumberInput(
                attrs={"class": "input input-neutral w-full", "step": "0.01"}
            ),
            "penalty": forms.NumberInput(
                attrs={"class": "input input-neutral w-full", "step": "0.01"}
            ),
            "interest": forms.NumberInput(
                attrs={"class": "input input-neutral w-full", "step": "0.01"}
            ),
            "monetary_adjust": forms.NumberInput(
                attrs={"class": "input input-neutral w-full", "step": "0.01"}
            ),
            "method": forms.Select(attrs={"class": "select select-neutral w-full"}),
            "notes": forms.TextInput(attrs={"class": "input input-neutral w-full"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only installments that still accept payments, plus the current one on edit.
        selectable = Installment.objects.filter(
            status__in=[InstallmentStatus.OPEN, InstallmentStatus.PARTIAL]
        )
        if self.instance.pk:
            selectable = selectable | Installment.objects.filter(
                pk=self.instance.installment_id
            )
        self.fields["installment"].queryset = selectable.select_related("account")

    def clean(self):
        cleaned_data = super().clean()
        installment = cleaned_data.get("installment")
        amount = cleaned_data.get("amount")
        if installment is None or amount is None:
            return cleaned_data

        charges = sum(
            (
                cleaned_data.get(name) or ZERO
                for name in ("penalty", "interest", "monetary_adjust")
            ),
            ZERO,
        )
        principal = amount - charges
        if principal <= 0:
            self.add_error(
                "amount",
                "O valor pago deve ser maior que a soma de multa, juros e correção.",
            )
            return cleaned_data

        balance = installment.balance()
        if self.instance.pk and self.instance.installment_id == installment.pk:
            # The payment being edited is already deducted from the balance.
            balance += self.instance.amount - (
                self.instance.penalty
                + self.instance.interest
                + self.instance.monetary_adjust
            )
        if principal > balance:
            self.add_error(
                "amount",
                f"O valor principal (R$ {principal}) excede o saldo da parcela "
                f"(R$ {balance}).",
            )
        return cleaned_data


class PaymentFilterForm(forms.Form):
    direction = forms.ChoiceField(
        label="Natureza",
        choices=[("", "Todas")] + Direction.choices,
        required=False,
        widget=forms.Select(attrs={"class": "select select-neutral select-sm w-full"}),
    )
    method = forms.ChoiceField(
        label="Forma de pagamento",
        choices=[("", "Todas")] + PaymentMethod.choices,
        required=False,
        widget=forms.Select(attrs={"class": "select select-neutral select-sm w-full"}),
    )
    paid_from = forms.DateField(
        label="Pago a partir de",
        required=False,
        widget=date_input("input input-neutral input-sm w-full"),
    )
    paid_to = forms.DateField(
        label="Pago até",
        required=False,
        widget=date_input("input input-neutral input-sm w-full"),
    )
