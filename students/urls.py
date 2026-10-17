from django.urls import path

from students.views import (
    GuardianCreateView,
    GuardianListView,
    GuardianUpdateView,
    StudentListView,
    student_add_view,
    student_edit_view,
)

app_name = "students"

urlpatterns = [
    path("guardians/list/", GuardianListView.as_view(), name="guardian_list"),
    path("guardians/add/", GuardianCreateView.as_view(), name="guardian_add"),
    path(
        "guardians/edit/<int:pk>/", GuardianUpdateView.as_view(), name="guardian_edit"
    ),
    path("list/", StudentListView.as_view(), name="student_list"),
    path("add/", student_add_view, name="student_add"),
    path("edit/<int:pk>/", student_edit_view, name="student_edit"),
]
