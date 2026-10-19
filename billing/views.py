from django.contrib import messages
from django.db.models import Count, IntegerField, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import DeleteView, DetailView, FormView, ListView, UpdateView

from accounts.views import SuccessMessageMixin
from base.search import HtmxFilterMixin, HtmxSearchMixin
from billing.forms import (
    BankSettingsForm,
    BankSlipFilterForm,
    RemittanceFilterForm,
    RemittanceForm,
    ReturnFileForm,
)
from billing.models import (
    BankSettings,
    BankSlip,
    EventStatus,
    Occurrence,
    Remittance,
    ReturnFile,
)
from billing.services import (
    BillingError,
    create_remittance,
    delete_remittance,
    import_return,
    payer_problems,
    punctuality_discount,
    remittance_candidates,
    write_off_candidates,
)

# BANK SETTINGS VIEWS


class BankSettingsUpdateView(SuccessMessageMixin, UpdateView):
    model = BankSettings
    form_class = BankSettingsForm
    template_name = "bank_settings/bank_settings_edit.html"
    success_url = reverse_lazy("billing:remittance_list")
    success_message = "Registro atualizado com sucesso"

    def get_object(self, queryset=None):
        return BankSettings.load() or BankSettings()


# REMITTANCE VIEWS


def _write_off_count():
    # Subquery: joining both slip relations would multiply the other totals.
    return Coalesce(
        Subquery(
            BankSlip.objects.filter(write_off_remittance=OuterRef("pk"))
            .values("write_off_remittance")
            .annotate(count=Count("pk"))
            .values("count"),
            output_field=IntegerField(),
        ),
        0,
    )


class RemittanceListView(HtmxSearchMixin, ListView):
    model = Remittance
    queryset = Remittance.objects.annotate(
        slips_count=Count("slips"),
        total=Sum("slips__amount"),
        write_offs_count=_write_off_count(),
    )
    template_name = "remittances/remittance_list.html"
    partial_template_name = "remittances/partials/remittance_table.html"
    context_object_name = "remittances"
    paginate_by = 10
    ordering = ("-number",)
    search_fields = ("number",)


class RemittanceCreateView(HtmxFilterMixin, ListView):
    """Lists installments that can be sent; POST generates the file."""

    template_name = "remittances/remittance_add.html"
    partial_template_name = "remittances/partials/remittance_candidates.html"
    context_object_name = "installments"
    filter_form_class = RemittanceFilterForm
    filter_lookups = {"due_from": "due_date__gte", "due_to": "due_date__lte"}
    search_fields = (
        "account__description",
        "account__guardian__name",
        "account__enrollment__student__name",
        "account__enrollment__student__registration",
    )
    ordering = ("due_date", "account__guardian__name", "pk")

    def get_queryset(self):
        return remittance_candidates()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rows = [
            {
                "installment": installment,
                "discount": punctuality_discount(installment, installment.outstanding),
                "problems": payer_problems(installment),
            }
            for installment in context["installments"]
        ]
        context.update(
            rows=rows,
            ready_count=sum(1 for row in rows if not row["problems"]),
            write_offs=write_off_candidates(),
            settings=BankSettings.load(),
        )
        return context

    def post(self, request, *args, **kwargs):
        form = RemittanceForm(request.POST)
        if not form.is_valid():
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
            return redirect(request.get_full_path())
        try:
            remittance = create_remittance(
                [installment.pk for installment in form.cleaned_data["installments"]],
                [slip.pk for slip in form.cleaned_data["write_offs"]],
            )
        except BillingError as exc:
            messages.error(request, str(exc))
            return redirect(request.get_full_path())
        messages.success(
            request,
            f"Registro cadastrado com sucesso: remessa {remittance.number} com "
            f"{remittance.slips.count()} boleto(s) e "
            f"{remittance.write_off_slips.count()} pedido(s) de baixa",
        )
        return redirect("billing:remittance_list")


class RemittanceDownloadView(DetailView):
    model = Remittance

    def render_to_response(self, context):
        response = HttpResponse(
            self.object.content.encode("ascii"), content_type="text/plain"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{self.object.filename}"'
        )
        return response


class RemittanceDeleteView(DeleteView):
    model = Remittance
    template_name = "remittances/remittance_delete.html"
    success_url = reverse_lazy("billing:remittance_list")

    def form_valid(self, form):
        try:
            delete_remittance(self.object)
        except BillingError as exc:
            messages.error(self.request, str(exc))
        else:
            messages.warning(self.request, "Registro deletado com sucesso")
        return redirect(self.success_url)


# BANK SLIP VIEWS


class BankSlipListView(HtmxFilterMixin, ListView):
    model = BankSlip
    queryset = BankSlip.objects.select_related(
        "remittance", "installment__account__guardian"
    )
    template_name = "bank_slips/bank_slip_list.html"
    partial_template_name = "bank_slips/partials/bank_slip_table.html"
    context_object_name = "slips"
    paginate_by = 10
    ordering = ("-pk",)
    filter_form_class = BankSlipFilterForm
    filter_lookups = {"due_from": "due_date__gte", "due_to": "due_date__lte"}
    search_fields = (
        "nosso_numero",
        "installment__account__description",
        "installment__account__guardian__name",
        "installment__account__enrollment__student__name",
    )


# RETURN FILE VIEWS


class ReturnFileListView(HtmxSearchMixin, ListView):
    model = ReturnFile
    queryset = ReturnFile.objects.annotate(
        events_count=Count("events"),
        errors_count=Count("events", filter=Q(events__status=EventStatus.ERROR)),
        paid_total=Sum("events__payment__amount"),
    )
    template_name = "return_files/return_file_list.html"
    partial_template_name = "return_files/partials/return_file_table.html"
    context_object_name = "return_files"
    paginate_by = 10
    ordering = ("-created_at",)
    search_fields = ("name",)


class ReturnFileCreateView(FormView):
    form_class = ReturnFileForm
    template_name = "return_files/return_file_add.html"

    def form_valid(self, form):
        file = form.cleaned_data["file"]
        try:
            self.object = import_return(file.name, file.read())
        except BillingError as exc:
            form.add_error("file", str(exc))
            return self.form_invalid(form)
        counts = self.object.events.aggregate(
            processed=Count("pk", filter=Q(status=EventStatus.PROCESSED)),
            errors=Count("pk", filter=Q(status=EventStatus.ERROR)),
            ignored=Count("pk", filter=Q(status=EventStatus.IGNORED)),
        )
        messages.success(
            self.request,
            f"Registro cadastrado com sucesso: {counts['processed']} processada(s), "
            f"{counts['errors']} com erro, {counts['ignored']} ignorada(s)",
        )
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("billing:return_file_detail", args=[self.object.pk])


class ReturnFileDetailView(DetailView):
    model = ReturnFile
    template_name = "return_files/return_file_detail.html"
    context_object_name = "return_file"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        events = self.object.events.select_related(
            "bank_slip__installment__account__guardian", "payment"
        )
        context["events"] = events
        labels = dict(Occurrence.choices)
        context["summary"] = [
            {**row, "label": labels.get(row["occurrence_code"], "Outra ocorrência")}
            for row in events.order_by("occurrence_code")
            .values("occurrence_code")
            .annotate(count=Count("pk"), paid=Sum("amount_paid"))
        ]
        return context
