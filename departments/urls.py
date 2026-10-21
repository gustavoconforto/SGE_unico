from django.urls import path

from departments.views import (
    DepartmentCreateView,
    DepartmentDeleteView,
    DepartmentListView,
    DepartmentUpdateView,
)

app_name = "departments"

urlpatterns = [
    path("list/", DepartmentListView.as_view(), name="department_list"),
    path("add/", DepartmentCreateView.as_view(), name="department_add"),
    path("edit/<int:pk>/", DepartmentUpdateView.as_view(), name="department_edit"),
    path(
        "delete/<int:pk>/", DepartmentDeleteView.as_view(), name="department_delete"
    ),
]
