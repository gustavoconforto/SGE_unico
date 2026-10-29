from django.contrib import messages
from django.db import transaction
from django.db.models import Count, ProtectedError, Q, Sum
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.text import format_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.forms import (
    AccountPayableFilterForm,
    AccountPayableForm,
    AccountReceivableFilterForm,
    AccountReceivableForm,
    AccountStatus,
    AccountTypeFilterForm,
    AccountTypeForm,
    InstallmentFilterForm,
    InstallmentFilterStatus,
    InstallmentForm,
    PayablePaymentForm,
    PaymentFilterForm,
    PaymentForm,
    SupplierForm,
    financial_guardians,
    installment_label,
)
from accounts.models import (
    PENDING_STATUSES,
    Account,
    AccountPayable,
    AccountReceivable,
    AccountType,
    Direction,
    Installment,
    InstallmentStatus,
    Payment,
    Supplier,
)
from accounts.services import build_installments
from base.search import HtmxFilterMixin, HtmxSearchMixin
from enrollments.models import Enrollment


class SuccessMessageMixin:
    success_message = None

    def form_valid(self, form):
        messages.success(self.request, self.success_message)
        return super().form_valid(form)


class ProtectedDeleteMixin:
    """DeleteView mixin: reports PROTECT foreign keys instead of raising."""

    protected_message = "Este registro está em uso e não pode ser deletado."

    def form_valid(self, form):
        try:
            self.object.delete()
        except ProtectedError:
            messages.error(self.request, self.protected_message)
        else:
            messages.warning(self.request, "Registro deletado com sucesso")
        return redirect(self.get_success_url())


# SUPPLIER VIEWS


class SupplierListView(HtmxSearchMixin, ListView):
    model = Supplier
    template_name = "suppliers/supplier_list.html"
    partial_template_name = "suppliers/partials/supplier_table.html"
    context_object_name = "suppliers"
    paginate_by = 10
    ordering = ("name",)
    search_fields = ("name", "document", "phone", "email", "notes")


class SupplierCreateView(SuccessMessageMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "suppliers/supplier_add.html"
    success_url = reverse_lazy("accounts:supplier_list")
    success_message = "Registro cadastrado com sucesso"


class SupplierUpdateView(SuccessMessageMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "suppliers/supplier_edit.html"
    success_url = reverse_lazy("accounts:supplier_list")
    success_message = "Registro atualizado com sucesso"


class SupplierDeleteView(ProtectedDeleteMixin, DeleteView):
    model = Supplier
    template_name = "suppliers/supplier_delete.html"
    success_url = reverse_lazy("accounts:supplier_list")
    protected_message = "Este fornecedor possui contas e não pode ser deletado."


# ACCOUNT TYPE VIEWS


class AccountTypeListView(HtmxFilterMixin, ListView):
    model = AccountType
    template_name = "account_types/account_type_list.html"
    partial_template_name = "account_types/partials/account_type_table.html"
    context_object_name = "account_types"
    paginate_by = 10
    ordering = ("direction", "name")
    filter_form_class = AccountTypeFilterForm
    search_fields = ("name",)

    def get_queryset(self):
        return super().get_queryset().annotate(accounts_count=Count("accounts"))


class AccountTypeCreateView(SuccessMessageMixin, CreateView):
    model = AccountType
    form_class = AccountTypeForm
    template_name = "account_types/account_type_add.html"
    success_url = reverse_lazy("accounts:account_type_list")
    success_message = "Registro cadastrado com sucesso"


class AccountTypeUpdateView(SuccessMessageMixin, UpdateView):
    model = AccountType
    form_class = AccountTypeForm
    template_name = "account_types/account_type_edit.html"
    success_url = reverse_lazy("accounts:account_type_list")
    success_message = "Registro atualizado com sucesso"


class AccountTypeDeleteView(ProtectedDeleteMixin, DeleteView):
    model = AccountType
    template_name = "account_types/account_type_delete.html"
    success_url = reverse_lazy("accounts:account_type_list")
    protected_message = "Esta categoria possui contas e não pode ser deletada."


# ACCOUNT VIEWS
# Receivable and payable accounts share templates; each view only states its
# proxy model, form and URL names. The mixin below feeds the templates.


class AccountContextMixin:
    url_prefix = None
    title = None
    noun = None
    counterpart_label = None

    def get_success_url(self):
        return reverse_lazy(f"accounts:{self.url_prefix}_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "title": self.title,
                "noun": self.noun,
                "counterpart_label": self.counterpart_label,
                "urls": {
                    action: f"accounts:{self.url_prefix}_{action}"
                    for action in ("list", "add", "edit", "delete")
                },
            }
        )
        return context


class InstallmentSummaryMixin:
    # Sits after HtmxFilterMixin in the MRO so the annotations exist before
    # filter_status runs. Annotated per request since "overdue" depends on today.
    def get_queryset(self):
        return super().get_queryset().with_installment_summary()


class AccountListMixin(AccountContextMixin, HtmxFilterMixin, InstallmentSummaryMixin):
    template_name = "accounts/account_list.html"
    partial_template_name = "accounts/partials/account_table.html"
    context_object_name = "accounts"
    paginate_by = 10
    ordering = ("-issue_date", "description")
    filter_lookups = {"issue_from": "issue_date__gte", "issue_to": "issue_date__lte"}

    def filter_status(self, queryset, value):
        conditions = {
            AccountStatus.PENDING: Q(installments_pending__gt=0),
            AccountStatus.OVERDUE: Q(installments_overdue__gt=0),
            AccountStatus.PAID: Q(installments_pending=0, installments_paid__gt=0),
            AccountStatus.CANCELLED: Q(
                installments_total__gt=0, installments_pending=0, installments_paid=0
            ),
        }
        return queryset.filter(conditions[value])


class AccountCreateMixin(AccountContextMixin):
    template_name = "accounts/account_add.html"

    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)
        Installment.objects.bulk_create(
            build_installments(
                self.object,
                form.cleaned_data["installments_count"],
                form.cleaned_data["first_due_date"],
            )
        )
        messages.success(self.request, "Registro cadastrado com sucesso")
        return response


class AccountUpdateMixin(AccountContextMixin):
    template_name = "accounts/account_edit.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["installments"] = self.object.installments.with_balance()
        return context

    def form_valid(self, form):
        messages.success(self.request, "Registro atualizado com sucesso")
        return super().form_valid(form)


class AccountDeleteMixin(AccountContextMixin):
    template_name = "accounts/account_delete.html"

    def form_valid(self, form):
        if Payment.objects.filter(installment__account=self.object).exists():
            messages.error(
                self.request,
                "Esta conta possui baixas registradas. Exclua as baixas antes.",
            )
            return redirect(self.get_success_url())
        try:
            with transaction.atomic():
                self.object.installments.all().delete()
                self.object.delete()
        except ProtectedError:
            messages.error(
                self.request,
                "Esta conta possui parcelas em uso (ex.: boletos) e não pode ser "
                "deletada.",
            )
            return redirect(self.get_success_url())
        messages.warning(self.request, "Registro deletado com sucesso")
        return redirect(self.get_success_url())


# ACCOUNT RECEIVABLE VIEWS


class AccountReceivableMixin:
    model = AccountReceivable
    url_prefix = "receivable"
    title = "Contas a receber"
    noun = "conta a receber"
    counterpart_label = "Responsável"


class AccountReceivableListView(AccountReceivableMixin, AccountListMixin, ListView):
    queryset = AccountReceivable.objects.select_related(
        "category", "guardian", "student"
    )
    filter_form_class = AccountReceivableFilterForm
    search_fields = (
        "description",
        "guardian__name",
        "student__name",
        "student__registration",
        "notes",
    )


class AccountReceivableCreateView(
    AccountReceivableMixin, AccountCreateMixin, CreateView
):
    form_class = AccountReceivableForm

    def get_enrollment(self):
        # "Nova conta a receber" on the enrollment page: ?enrollment=<pk>
        pk = self.request.GET.get("enrollment", "")
        if not pk.isdigit():
            return None
        return Enrollment.objects.select_related("student").filter(pk=pk).first()

    def get_initial(self):
        initial = super().get_initial()
        enrollment = self.get_enrollment()
        if enrollment:
            initial.update(
                student=enrollment.student,
                guardian=financial_guardians(enrollment.student_id).first(),
            )
        return initial

    def get_back_url(self):
        enrollment = self.get_enrollment()
        if enrollment:
            return reverse("enrollments:enrollment_edit", kwargs={"pk": enrollment.pk})
        return reverse(f"accounts:{self.url_prefix}_list")

    def get_success_url(self):
        return self.get_back_url()

    def get_context_data(self, **kwargs):
        return super().get_context_data(back_url=self.get_back_url(), **kwargs)


class ReceivableGuardianOptionsView(TemplateView):
    """htmx endpoint: the guardian select filtered by ?student=<pk>."""

    template_name = "accounts/partials/guardian_field.html"

    def get_context_data(self, **kwargs):
        student = self.request.GET.get("student", "")
        initial = {}
        if student.isdigit():
            initial = {
                "student": student,
                "guardian": financial_guardians(student).first(),
            }
        form = AccountReceivableForm(initial=initial)
        return super().get_context_data(form=form, **kwargs)


class AccountReceivableUpdateView(
    AccountReceivableMixin, AccountUpdateMixin, UpdateView
):
    form_class = AccountReceivableForm


class AccountReceivableDeleteView(
    AccountReceivableMixin, AccountDeleteMixin, DeleteView
):
    pass


# ACCOUNT PAYABLE VIEWS


class AccountPayableMixin:
    model = AccountPayable
    url_prefix = "payable"
    title = "Contas a pagar"
    noun = "conta a pagar"
    counterpart_label = "Fornecedor"


class AccountPayableListView(AccountPayableMixin, AccountListMixin, ListView):
    queryset = AccountPayable.objects.select_related("category", "supplier")
    filter_form_class = AccountPayableFilterForm
    search_fields = ("description", "supplier__name", "supplier__document", "notes")
    extra_context = {"show_payment_dates": True}

    def get_queryset(self):
        return super().get_queryset().with_payment_dates()


class AccountPayableCreateView(AccountPayableMixin, AccountCreateMixin, CreateView):
    form_class = AccountPayableForm


class AccountPayableUpdateView(AccountPayableMixin, AccountUpdateMixin, UpdateView):
    form_class = AccountPayableForm


class AccountPayableDeleteView(AccountPayableMixin, AccountDeleteMixin, DeleteView):
    pass


# INSTALLMENT VIEWS


class InstallmentListView(HtmxFilterMixin, ListView):
    model = Installment
    queryset = Installment.objects.select_related(
        "account__guardian", "account__supplier", "account__enrollment__student"
    )
    template_name = "installments/installment_list.html"
    context_object_name = "installments"
    partial_template_name = "installments/partials/installment_table.html"
    paginate_by = 10
    ordering = ("due_date", "account__description", "number")
    filter_form_class = InstallmentFilterForm
    filter_lookups = {
        "direction": "account__direction",
        "due_from": "due_date__gte",
        "due_to": "due_date__lte",
    }
    search_fields = (
        "account__description",
        "account__guardian__name",
        "account__supplier__name",
        "account__enrollment__student__name",
        "account__enrollment__student__registration",
    )

    def get_queryset(self):
        return super().get_queryset().with_balance()

    def filter_status(self, queryset, value):
        if value == InstallmentFilterStatus.PENDING:
            return queryset.pending()
        if value == InstallmentFilterStatus.OVERDUE:
            return queryset.overdue()
        return queryset.filter(status=value)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Totals over the whole filtered set (not just the current page),
        # split by direction since receivables and payables don't add up.
        receivable = Q(account__direction=Direction.RECEIVABLE)
        payable = Q(account__direction=Direction.PAYABLE)
        paid = Q(status=InstallmentStatus.PAID)
        context["totals"] = self.object_list.order_by().aggregate(
            receivable_amount=Sum("amount", filter=receivable),
            receivable_outstanding=Sum("outstanding", filter=receivable),
            receivable_paid=Sum("amount", filter=receivable & paid),
            payable_amount=Sum("amount", filter=payable),
            payable_outstanding=Sum("outstanding", filter=payable),
            payable_paid=Sum("amount", filter=payable & paid),
        )
        return context


class InstallmentCreateView(CreateView):
    model = Installment
    template_name = "installments/installment_add.html"
    form_class = InstallmentForm
    success_url = reverse_lazy("accounts:installment_list")

    def get_initial(self):
        # Allows "Adicionar parcela" links from other pages: ?account=<pk>
        initial = super().get_initial()
        account = Account.objects.filter(
            pk=self.request.GET.get("account") or None
        ).first()
        if account:
            initial["account"] = account
        return initial

    def form_valid(self, form):
        messages.success(self.request, "Parcela cadastrada com sucesso")
        return super().form_valid(form)


# PAYMENT VIEWS


class PaymentListView(HtmxFilterMixin, ListView):
    model = Payment
    queryset = Payment.objects.select_related(
        "installment__account__guardian", "installment__account__supplier"
    )
    template_name = "payments/payment_list.html"
    context_object_name = "payments"
    partial_template_name = "payments/partials/payment_table.html"
    paginate_by = 10
    ordering = ("-paid_at", "-pk")
    filter_form_class = PaymentFilterForm
    filter_lookups = {
        "direction": "installment__account__direction",
        "paid_from": "paid_at__gte",
        "paid_to": "paid_at__lte",
    }
    search_fields = (
        "installment__account__description",
        "installment__account__guardian__name",
        "installment__account__supplier__name",
        "notes",
    )


class ReceivableInstallmentLookupView(HtmxSearchMixin, ListView):
    """Options for the installment search box in the receivable payment form."""

    direction = Direction.RECEIVABLE
    queryset = (
        Installment.objects.pending()
        .with_balance()
        .select_related("account__guardian", "account__supplier")
    )
    template_name = "payments/partials/installment_options.html"
    context_object_name = "installments"
    paginate_by = 10
    ordering = ("due_date", "pk")
    search_fields = ("account__description", "account__guardian__name")

    def get_queryset(self):
        return super().get_queryset().filter(account__direction=self.direction)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for installment in context["installments"]:
            installment.label = installment_label(installment)
        return context


class PayableInstallmentLookupView(ReceivableInstallmentLookupView):
    """Options for the installment search box in the payable payment form."""

    direction = Direction.PAYABLE
    search_fields = (
        "account__description",
        "account__supplier__name",
        "account__supplier__document",
    )


class PaymentCreateView(CreateView):
    model = Payment
    template_name = "payments/payment_add.html"
    form_class = PaymentForm
    success_url = reverse_lazy("accounts:payment_list")
    success_message = "Baixa registrada com sucesso"

    def get_initial(self):
        # Allows "Baixar" links from the account page: ?installment=<pk>
        initial = super().get_initial()
        installment = Installment.objects.filter(
            pk=self.request.GET.get("installment") or None,
            status__in=PENDING_STATUSES,
            account__direction=self.form_class.direction,
        ).first()
        if installment:
            initial.update(
                installment=installment,
                amount=installment.balance(),
                paid_at=timezone.localdate(),
            )
        return initial

    def form_valid(self, form):
        messages.success(self.request, self.success_message)
        return super().form_valid(form)


class PaymentUpdateView(UpdateView):
    model = Payment
    template_name = "payments/payment_edit.html"
    form_class = PaymentForm
    success_url = reverse_lazy("accounts:payment_list")
    success_message = "Baixa atualizada com sucesso"

    def get_queryset(self):
        # Each form only edits payments of its own direction.
        return (
            super()
            .get_queryset()
            .filter(installment__account__direction=self.form_class.direction)
        )

    def form_valid(self, form):
        previous_installment = Payment.objects.get(pk=self.object.pk).installment
        with transaction.atomic():
            response = super().form_valid(form)
            if previous_installment.pk != self.object.installment_id:
                previous_installment.refresh_status()
        messages.success(self.request, self.success_message)
        return response


class PayablePaymentCreateView(PaymentCreateView):
    template_name = "payments/payable_payment_add.html"
    form_class = PayablePaymentForm
    success_url = format_lazy("{}?direction=P", reverse_lazy("accounts:payment_list"))
    success_message = "Pagamento registrado com sucesso"


class PayablePaymentUpdateView(PaymentUpdateView):
    template_name = "payments/payable_payment_edit.html"
    form_class = PayablePaymentForm
    success_url = format_lazy("{}?direction=P", reverse_lazy("accounts:payment_list"))
    success_message = "Pagamento atualizado com sucesso"


class PaymentDeleteView(DeleteView):
    model = Payment
    template_name = "payments/payment_delete.html"
    success_url = reverse_lazy("accounts:payment_list")

    def form_valid(self, form):
        messages.warning(self.request, "Baixa deletada com sucesso")
        return super().form_valid(form)
