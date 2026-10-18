from django.urls import path

from accounts.views import (
    AccountTypeCreateView,
    AccountTypeDeleteView,
    AccountTypeListView,
    AccountTypeUpdateView,
    AccountPayableCreateView,
    AccountPayableDeleteView,
    AccountPayableListView,
    AccountPayableUpdateView,
    AccountReceivableCreateView,
    AccountReceivableDeleteView,
    AccountReceivableListView,
    AccountReceivableUpdateView,
    InstallmentCreateView,
    InstallmentListView,
    PaymentCreateView,
    PaymentDeleteView,
    PaymentListView,
    PaymentUpdateView,
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
    path(
        "categories/list/", AccountTypeListView.as_view(), name="account_type_list"
    ),
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
        "installments/list/", InstallmentListView.as_view(), name="installment_list"
    ),
    path(
        "installments/add/", InstallmentCreateView.as_view(), name="installment_add"
    ),
    path("payments/list/", PaymentListView.as_view(), name="payment_list"),
    path("payments/add/", PaymentCreateView.as_view(), name="payment_add"),
    path(
        "payments/edit/<int:pk>/",
        PaymentUpdateView.as_view(),
        name="payment_edit",
    ),
    path(
        "payments/delete/<int:pk>/",
        PaymentDeleteView.as_view(),
        name="payment_delete",
    ),
]
