from django.urls import path

from accounts.views import (
    AccountPayableCreateView,
    AccountPayableDeleteView,
    AccountPayableListView,
    AccountPayablePdfView,
    AccountPayableReceiptView,
    AccountPayableUpdateView,
    AccountReceivableCreateView,
    AccountReceivableDeleteView,
    AccountReceivableListView,
    AccountReceivablePdfView,
    AccountReceivableReceiptView,
    AccountReceivableUpdateView,
    AccountTypeCreateView,
    AccountTypeDeleteView,
    AccountTypeListView,
    AccountTypeUpdateView,
    InstallmentCreateView,
    InstallmentListView,
    PayableInstallmentLookupView,
    PayablePaymentCreateView,
    PayablePaymentUpdateView,
    PaymentCreateView,
    PaymentDeleteView,
    PaymentListView,
    PaymentUpdateView,
    ReceivableGuardianOptionsView,
    ReceivableInstallmentLookupView,
    SupplierCreateView,
    SupplierDeleteView,
    SupplierListView,
    SupplierUpdateView,
)

app_name = "accounts"

urlpatterns = [
    path("suppliers/list/", SupplierListView.as_view(), name="supplier_list"),
    path("suppliers/add/", SupplierCreateView.as_view(), name="supplier_add"),
    path(
        "suppliers/edit/<int:pk>/", SupplierUpdateView.as_view(), name="supplier_edit"
    ),
    path(
        "suppliers/delete/<int:pk>/",
        SupplierDeleteView.as_view(),
        name="supplier_delete",
    ),
    path("categories/list/", AccountTypeListView.as_view(), name="account_type_list"),
    path("categories/add/", AccountTypeCreateView.as_view(), name="account_type_add"),
    path(
        "categories/edit/<int:pk>/",
        AccountTypeUpdateView.as_view(),
        name="account_type_edit",
    ),
    path(
        "categories/delete/<int:pk>/",
        AccountTypeDeleteView.as_view(),
        name="account_type_delete",
    ),
    path(
        "receivable/list/",
        AccountReceivableListView.as_view(),
        name="receivable_list",
    ),
    path(
        "receivable/add/",
        AccountReceivableCreateView.as_view(),
        name="receivable_add",
    ),
    path(
        "receivable/edit/<int:pk>/",
        AccountReceivableUpdateView.as_view(),
        name="receivable_edit",
    ),
    path(
        "receivable/delete/<int:pk>/",
        AccountReceivableDeleteView.as_view(),
        name="receivable_delete",
    ),
    path(
        "receivable/guardian-options/",
        ReceivableGuardianOptionsView.as_view(),
        name="receivable_guardian_options",
    ),
    path(
        "receivable/print/<int:pk>/",
        AccountReceivableReceiptView.as_view(),
        name="receivable_print",
    ),
    path(
        "receivable/print/pdf/<int:pk>/",
        AccountReceivablePdfView.as_view(),
        name="receivable_pdf",
    ),
    path("payable/list/", AccountPayableListView.as_view(), name="payable_list"),
    path("payable/add/", AccountPayableCreateView.as_view(), name="payable_add"),
    path(
        "payable/edit/<int:pk>/",
        AccountPayableUpdateView.as_view(),
        name="payable_edit",
    ),
    path(
        "payable/delete/<int:pk>/",
        AccountPayableDeleteView.as_view(),
        name="payable_delete",
    ),
    path(
        "payable/print/<int:pk>/",
        AccountPayableReceiptView.as_view(),
        name="payable_print",
    ),
    path(
        "payable/print/pdf/<int:pk>/",
        AccountPayablePdfView.as_view(),
        name="payable_pdf",
    ),
    path("installments/list/", InstallmentListView.as_view(), name="installment_list"),
    path("installments/add/", InstallmentCreateView.as_view(), name="installment_add"),
    path(
        "installments/lookup/receivable/",
        ReceivableInstallmentLookupView.as_view(),
        name="receivable_installment_lookup",
    ),
    path(
        "installments/lookup/payable/",
        PayableInstallmentLookupView.as_view(),
        name="payable_installment_lookup",
    ),
    path("payments/list/", PaymentListView.as_view(), name="payment_list"),
    path("payments/add/", PaymentCreateView.as_view(), name="payment_add"),
    path(
        "payments/edit/<int:pk>/",
        PaymentUpdateView.as_view(),
        name="payment_edit",
    ),
    path(
        "payments/payable/add/",
        PayablePaymentCreateView.as_view(),
        name="payable_payment_add",
    ),
    path(
        "payments/payable/edit/<int:pk>/",
        PayablePaymentUpdateView.as_view(),
        name="payable_payment_edit",
    ),
    path(
        "payments/delete/<int:pk>/",
        PaymentDeleteView.as_view(),
        name="payment_delete",
    ),
]
