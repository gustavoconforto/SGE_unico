from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from employees.forms import EmployeeForm, EmployeeRoleTypeForm
from employees.models import Employee, EmployeeRoleType

######### EMPLOYEE VIEWS #########


class EmployeeListView(ListView):
    model = Employee
    template_name = "employees/employee_list.html"
    context_object_name = "employees"
    paginate_by = 10


class EmployeeCreateView(CreateView):
    model = Employee
    template_name = "employees/employee_add.html"
    form_class = EmployeeForm
    success_url = reverse_lazy("employees:employee_list")


class EmployeeUpdateView(UpdateView):
    model = Employee
    template_name = "employees/employee_edit.html"
    form_class = EmployeeForm
    success_url = reverse_lazy("employees:employee_list")


class EmployeeDeleteView(DeleteView):
    model = Employee
    template_name = "employees/employee_delete.html"
    success_url = reverse_lazy("employees:employee_list")


######### EMPLOYEE_ROLES VIEWS #########


class EmployeeRoleListView(ListView):
    model = EmployeeRoleType
    template_name = "employees/employee_role_list.html"
    context_object_name = "employee_roles"
    paginate_by = 10


class EmployeeRoleCreateView(CreateView):
    model = EmployeeRoleType
    template_name = "employees/employee_role_add.html"
    form_class = EmployeeRoleTypeForm
    success_url = reverse_lazy("employees:employee_role_list")


class EmployeeRoleUpdateView(UpdateView):
    model = EmployeeRoleType
    template_name = "employees/employee_role_edit.html"
    form_class = EmployeeRoleTypeForm
    success_url = reverse_lazy("employees:employee_role_list")


class EmployeeRoleDeleteView(DeleteView):
    model = EmployeeRoleType
    template_name = "employees/employee_role_delete.html"
    success_url = reverse_lazy("employees:employee_role_list")
