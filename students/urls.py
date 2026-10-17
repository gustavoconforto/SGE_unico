from django.urls import path

from students.views import (
    guardian_add_view,
    guardian_delete_view,
    guardian_edit_view,
    guardian_list_view,
    student_add_view,
    student_delete_view,
    student_edit_view,
    student_list_view,
)

app_name = "students"

urlpatterns = [
    path("guardians/list/", guardian_list_view, name="guardian_list"),
    path("guardians/add/", guardian_add_view, name="guardian_add"),
    path("guardians/edit/<int:pk>/", guardian_edit_view, name="guardian_edit"),
    path("guardians/delete/<int:pk>/", guardian_delete_view, name="guardian_delete"),
    path("list/", student_list_view, name="student_list"),
    path("add/", student_add_view, name="student_add"),
    path("edit/<int:pk>/", student_edit_view, name="student_edit"),
    path("delete/<int:pk>/", student_delete_view, name="student_delete"),
]
