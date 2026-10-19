from django.contrib import admin

from billing.models import BankSettings, BankSlip, Remittance, ReturnEvent, ReturnFile


@admin.register(BankSettings)
class BankSettingsAdmin(admin.ModelAdmin):
    list_display = ("company_name", "company_code", "agency", "account", "carteira")


@admin.register(Remittance)
class RemittanceAdmin(admin.ModelAdmin):
    list_display = ("number", "generated_at")
    exclude = ("content",)


@admin.register(BankSlip)
class BankSlipAdmin(admin.ModelAdmin):
    list_display = ("nosso_numero", "installment", "due_date", "amount", "status")
    list_filter = ("status",)
    search_fields = ("nosso_numero",)
    raw_id_fields = ("installment", "remittance")


@admin.register(ReturnFile)
class ReturnFileAdmin(admin.ModelAdmin):
    list_display = ("name", "file_date", "created_at")
    exclude = ("content",)


@admin.register(ReturnEvent)
class ReturnEventAdmin(admin.ModelAdmin):
    list_display = ("return_file", "sequence", "occurrence_code", "nosso_numero", "status")
    list_filter = ("status", "occurrence_code")
    raw_id_fields = ("bank_slip", "payment")
