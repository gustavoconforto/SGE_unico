from django.urls import path

from employees.views import (
    EmployeeCreateView,
    EmployeeDeleteView,
    EmployeeListView,
    EmployeeRoleCreateView,
    EmployeeRoleDeleteView,
    EmployeeRoleListView,
    EmployeeRoleUpdateView,
    EmployeeUpdateView,
)

app_name = "employees"

urlpatterns = [
    path("list/", EmployeeListView.as_view(), name="employee_list"),
    path("add/", EmployeeCreateView.as_view(), name="employee_add"),
    path("edit/<int:pk>/", EmployeeUpdateView.as_view(), name="employee_edit"),
    path("delete/<int:pk>/", EmployeeDeleteView.as_view(), name="employee_delete"),
    path("roles/list/", EmployeeRoleListView.as_view(), name="employee_role_list"),
    path("roles/add/", EmployeeRoleCreateView.as_view(), name="employee_role_add"),
    path(
        "roles/edit/<int:pk>/",
        EmployeeRoleUpdateView.as_view(),
        name="employee_role_edit",
    ),
    path(
        "roles/delete/<int:pk>/",
        EmployeeRoleDeleteView.as_view(),
        name="employee_role_delete",
    ),
]
