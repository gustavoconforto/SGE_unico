from django.urls import path

from incidents.views import (
    BathroomPermissionCreateView,
    BathroomPermissionDeleteView,
    BathroomPermissionListView,
    BathroomPermissionUpdateView,
    IncidentCreateView,
    IncidentDeleteView,
    IncidentGradesAll,
    IncidentGradesIndividual,
    IncidentListView,
    IncidentTypeCreateView,
    IncidentTypeDeleteView,
    IncidentTypeListView,
    IncidentTypeUpdateView,
    IncidentUpdateView,
    StudentDelayCreateView,
    StudentDelayDeleteView,
    StudentDelayListView,
    StudentDelayUpdateView,
)

app_name = "incidents"

urlpatterns = [
    path(
        "grades/individual",
        IncidentGradesIndividual.as_view(),
        name="incident_grades_individual",
    ),
    path("grades/all", IncidentGradesAll.as_view(), name="incident_grades_all"),
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
    path("delay/list/", StudentDelayListView.as_view(), name="student_delay_list"),
    path("delay/add/", StudentDelayCreateView.as_view(), name="student_delay_add"),
    path(
        "delay/edit/<int:pk>/",
        StudentDelayUpdateView.as_view(),
        name="student_delay_edit",
    ),
    path(
        "delay/delete/<int:pk>/",
        StudentDelayDeleteView.as_view(),
        name="student_delay_delete",
    ),
    path(
        "bathroom/list/",
        BathroomPermissionListView.as_view(),
        name="bathroom_permission_list",
    ),
    path(
        "bathroom/add/",
        BathroomPermissionCreateView.as_view(),
        name="bathroom_permission_add",
    ),
    path(
        "bathroom/edit/<int:pk>/",
        BathroomPermissionUpdateView.as_view(),
        name="bathroom_permission_edit",
    ),
    path(
        "bathroom/delete/<int:pk>/",
        BathroomPermissionDeleteView.as_view(),
        name="bathroom_permission_delete",
    ),
]
