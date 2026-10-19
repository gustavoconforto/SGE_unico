from django.urls import path

from billing.views import (
    BankSettingsUpdateView,
    BankSlipListView,
    RemittanceCreateView,
    RemittanceDeleteView,
    RemittanceDownloadView,
    RemittanceListView,
    ReturnFileCreateView,
    ReturnFileDetailView,
    ReturnFileListView,
)

app_name = "billing"

urlpatterns = [
    path("settings/edit/", BankSettingsUpdateView.as_view(), name="bank_settings_edit"),
    path("remittances/list/", RemittanceListView.as_view(), name="remittance_list"),
    path("remittances/add/", RemittanceCreateView.as_view(), name="remittance_add"),
    path(
        "remittances/download/<int:pk>/",
        RemittanceDownloadView.as_view(),
        name="remittance_download",
    ),
    path(
        "remittances/delete/<int:pk>/",
        RemittanceDeleteView.as_view(),
        name="remittance_delete",
    ),
    path("slips/list/", BankSlipListView.as_view(), name="bank_slip_list"),
    path("returns/list/", ReturnFileListView.as_view(), name="return_file_list"),
    path("returns/add/", ReturnFileCreateView.as_view(), name="return_file_add"),
    path(
        "returns/detail/<int:pk>/",
        ReturnFileDetailView.as_view(),
        name="return_file_detail",
    ),
]
