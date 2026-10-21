from django.urls import path

from incidents.views import (
    IncidentCreateView,
    IncidentDeleteView,
    IncidentListView,
    IncidentTypeCreateView,
    IncidentTypeDeleteView,
    IncidentTypeListView,
    IncidentTypeUpdateView,
    IncidentUpdateView,
)

app_name = "incidents"

urlpatterns = [
    path("list/", IncidentListView.as_view(), name="incident_list"),
    path("add/", IncidentCreateView.as_view(), name="incident_add"),
    path("edit/<int:pk>/", IncidentUpdateView.as_view(), name="incident_edit"),
    path("delete/<int:pk>/", IncidentDeleteView.as_view(), name="incident_delete"),
    path("type/list/", IncidentTypeListView.as_view(), name="incident_type_list"),
    path("type/add/", IncidentTypeCreateView.as_view(), name="incident_type_add"),
    path(
        "type/edit/<int:pk>/",
        IncidentTypeUpdateView.as_view(),
        name="incident_type_edit",
    ),
    path(
        "type/delete/<int:pk>/",
        IncidentTypeDeleteView.as_view(),
        name="incident_type_delete",
    ),
]
