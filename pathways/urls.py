from django.urls import path

from pathways.views import (
    ExtraGradesAll,
    ExtraGradeSettingsListView,
    ExtraGradeSettingsUpdateView,
    ExtraGradesIndividual,
    PathwayCreateView,
    PathwayDeleteView,
    PathwayEnrollmentCreateView,
    PathwayEnrollmentDeleteView,
    PathwayEnrollmentListView,
    PathwayEnrollmentUpdateView,
    PathwayGradeEntryView,
    PathwayListView,
    PathwayOfferingCreateView,
    PathwayOfferingDeleteView,
    PathwayOfferingListView,
    PathwayOfferingUpdateView,
    PathwaySessionAttendanceView,
    PathwaySessionCreateView,
    PathwaySessionDeleteView,
    PathwaySessionListView,
    PathwaySessionUpdateView,
    PathwayUpdateView,
)

app_name = "pathways"

urlpatterns = [
    path("list/", PathwayListView.as_view(), name="pathway_list"),
    path("add/", PathwayCreateView.as_view(), name="pathway_add"),
    path("edit/<int:pk>/", PathwayUpdateView.as_view(), name="pathway_edit"),
    path("delete/<int:pk>/", PathwayDeleteView.as_view(), name="pathway_delete"),
    path(
        "offerings/list/",
        PathwayOfferingListView.as_view(),
        name="pathway_offering_list",
    ),
    path(
        "offerings/add/",
        PathwayOfferingCreateView.as_view(),
        name="pathway_offering_add",
    ),
    path(
        "offerings/edit/<int:pk>/",
        PathwayOfferingUpdateView.as_view(),
        name="pathway_offering_edit",
    ),
    path(
        "offerings/delete/<int:pk>/",
        PathwayOfferingDeleteView.as_view(),
        name="pathway_offering_delete",
    ),
    path(
        "enrollments/list/",
        PathwayEnrollmentListView.as_view(),
        name="pathway_enrollment_list",
    ),
    path(
        "enrollments/add/",
        PathwayEnrollmentCreateView.as_view(),
        name="pathway_enrollment_add",
    ),
    path(
        "enrollments/edit/<int:pk>/",
        PathwayEnrollmentUpdateView.as_view(),
        name="pathway_enrollment_edit",
    ),
    path(
        "enrollments/delete/<int:pk>/",
        PathwayEnrollmentDeleteView.as_view(),
        name="pathway_enrollment_delete",
    ),
    path(
        "sessions/list/",
        PathwaySessionListView.as_view(),
        name="pathway_session_list",
    ),
    path(
        "sessions/add/",
        PathwaySessionCreateView.as_view(),
        name="pathway_session_add",
    ),
    path(
        "sessions/edit/<int:pk>/",
        PathwaySessionUpdateView.as_view(),
        name="pathway_session_edit",
    ),
    path(
        "sessions/delete/<int:pk>/",
        PathwaySessionDeleteView.as_view(),
        name="pathway_session_delete",
    ),
    path(
        "sessions/attendance/<int:pk>/",
        PathwaySessionAttendanceView.as_view(),
        name="pathway_session_attendance",
    ),
    path("grades/entry/", PathwayGradeEntryView.as_view(), name="pathway_grade_entry"),
    path(
        "extra_grades/individual/",
        ExtraGradesIndividual.as_view(),
        name="extra_grades_individual",
    ),
    path("extra_grades/all/", ExtraGradesAll.as_view(), name="extra_grades_all"),
    path(
        "extra_grade_settings/list/",
        ExtraGradeSettingsListView.as_view(),
        name="extra_grade_settings_list",
    ),
    path(
        "extra_grade_settings/edit/<int:school_year_pk>/",
        ExtraGradeSettingsUpdateView.as_view(),
        name="extra_grade_settings_edit",
    ),
]
