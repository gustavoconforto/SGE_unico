from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.views import ProtectedDeleteMixin, SuccessMessageMixin
from base.search import HtmxSearchMixin
from employees.forms import EmployeeForm, EmployeeRoleTypeForm
from employees.models import Employee, EmployeeRoleType

######### EMPLOYEE VIEWS #########


class EmployeeListView(HtmxSearchMixin, ListView):
    model = Employee
    template_name = "employees/employee_list.html"
    context_object_name = "employees"
    partial_template_name = "employees/partials/employee_table.html"
    paginate_by = 10
    ordering = ("name",)
    search_fields = ("name", "cpf", "role__role")


class EmployeeCreateView(SuccessMessageMixin, CreateView):
    model = Employee
    template_name = "employees/employee_add.html"
    form_class = EmployeeForm
    success_url = reverse_lazy("employees:employee_list")
    success_message = "Registro cadastrado com sucesso"


class EmployeeUpdateView(SuccessMessageMixin, UpdateView):
    model = Employee
    template_name = "employees/employee_edit.html"
    form_class = EmployeeForm
    success_url = reverse_lazy("employees:employee_list")
    success_message = "Registro atualizado com sucesso"


class EmployeeDeleteView(ProtectedDeleteMixin, DeleteView):
    model = Employee
    template_name = "employees/employee_delete.html"
    success_url = reverse_lazy("employees:employee_list")


######### EMPLOYEE_ROLES VIEWS #########


class EmployeeRoleListView(HtmxSearchMixin, ListView):
    model = EmployeeRoleType
    template_name = "employees/employee_role_list.html"
    context_object_name = "employee_roles"
    partial_template_name = "employees/partials/employee_role_table.html"
    paginate_by = 10
    ordering = ("role",)
    search_fields = ("role",)


class EmployeeRoleCreateView(SuccessMessageMixin, CreateView):
    model = EmployeeRoleType
    template_name = "employees/employee_role_add.html"
    form_class = EmployeeRoleTypeForm
    success_url = reverse_lazy("employees:employee_role_list")
    success_message = "Registro cadastrado com sucesso"


class EmployeeRoleUpdateView(SuccessMessageMixin, UpdateView):
    model = EmployeeRoleType
    template_name = "employees/employee_role_edit.html"
    form_class = EmployeeRoleTypeForm
    success_url = reverse_lazy("employees:employee_role_list")
    success_message = "Registro atualizado com sucesso"


class EmployeeRoleDeleteView(ProtectedDeleteMixin, DeleteView):
    model = EmployeeRoleType
    template_name = "employees/employee_role_delete.html"
    success_url = reverse_lazy("employees:employee_role_list")
