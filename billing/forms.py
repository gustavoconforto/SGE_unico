from django import forms

from accounts.forms import date_input
from billing.models import BankSettings, BankSlip, SlipStatus
from billing.services import remittance_candidates, write_off_candidates

MAX_RETURN_SIZE = 5 * 1024 * 1024


class BankSettingsForm(forms.ModelForm):
    class Meta:
        model = BankSettings
        fields = [
            "company_code",
            "company_name",
            "carteira",
            "agency",
            "account",
            "account_digit",
            "fine_percent",
            "monthly_interest_percent",
            "last_remittance_number",
        ]
        widgets = {
            "company_code": forms.TextInput(
                attrs={"class": "input input-neutral w-full", "inputmode": "numeric"}
            ),
            "company_name": forms.TextInput(attrs={"class": "input input-neutral w-full"}),
            "carteira": forms.TextInput(attrs={"class": "input input-neutral w-full"}),
            "agency": forms.TextInput(attrs={"class": "input input-neutral w-full"}),
            "account": forms.TextInput(attrs={"class": "input input-neutral w-full"}),
            "account_digit": forms.TextInput(
                attrs={"class": "input input-neutral w-full"}
            ),
            "fine_percent": forms.NumberInput(
                attrs={"class": "input input-neutral w-full", "step": "0.01"}
            ),
            "monthly_interest_percent": forms.NumberInput(
                attrs={"class": "input input-neutral w-full", "step": "0.01"}
            ),
            "last_remittance_number": forms.NumberInput(
                attrs={"class": "input input-neutral w-full"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        for name in ("company_code", "carteira", "agency", "account"):
            value = cleaned_data.get(name)
            if value and not value.isdigit():
                self.add_error(name, "Informe somente números.")
        carteira = cleaned_data.get("carteira")
        if carteira and len(carteira.lstrip("0") or "0") > 2:
            self.add_error("carteira", "A carteira deve ter 2 dígitos.")
        return cleaned_data


class RemittanceFilterForm(forms.Form):
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


class RemittanceForm(forms.Form):
    installments = forms.ModelMultipleChoiceField(queryset=None, required=False)
    write_offs = forms.ModelMultipleChoiceField(queryset=None, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["installments"].queryset = remittance_candidates()
        self.fields["write_offs"].queryset = BankSlip.objects.filter(
            pk__in=[slip.pk for slip in write_off_candidates()]
        )

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("installments") and not cleaned_data.get("write_offs"):
            raise forms.ValidationError(
                "Selecione ao menos uma parcela ou um pedido de baixa."
            )
        return cleaned_data


class BankSlipFilterForm(forms.Form):
    status = forms.ChoiceField(
        label="Situação",
        choices=[("", "Todas")] + SlipStatus.choices,
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


class ReturnFileForm(forms.Form):
    file = forms.FileField(
        label="Arquivo de retorno (.RET)",
        widget=forms.ClearableFileInput(
            attrs={"class": "file-input file-input-neutral w-full", "accept": ".ret,.RET"}
        ),
    )

    def clean_file(self):
        file = self.cleaned_data["file"]
        if file.size > MAX_RETURN_SIZE:
            raise forms.ValidationError("Arquivo muito grande.")
        return file
