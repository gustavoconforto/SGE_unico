from django.urls import path

from employees.views import (
    employee_add_view,
    employee_delete_view,
    employee_edit_view,
    employee_list_view,
    employee_role_add_view,
    employee_role_delete_view,
    employee_role_edit_view,
    employee_role_list_view,
)

app_name = "employees"

urlpatterns = [
    path("list/", employee_list_view, name="employee_list"),
    path("add/", employee_add_view, name="employee_add"),
    path("edit/<int:pk>/", employee_edit_view, name="employee_edit"),
    path("delete/<int:pk>/", employee_delete_view, name="employee_delete"),
    path("roles/list/", employee_role_list_view, name="employee_role_list"),
    path("roles/add/", employee_role_add_view, name="employee_role_add"),
    path(
        "roles/edit/<int:pk>/",
        employee_role_edit_view,
        name="employee_role_edit",
    ),
    path(
        "roles/delete/<int:pk>/",
        employee_role_delete_view,
        name="employee_role_delete",
    ),
]
