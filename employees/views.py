from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from employees.forms import EmployeeForm, EmployeeRoleTypeForm
from employees.models import Employee, EmployeeRoleType

# EMPLOYEE VIEWS


def employee_list_view(request):
    employees = Employee.objects.all()

    context = {"employees": employees}
    return render(request, "employees/employee_list.html", context)


def employee_add_view(request):
    if request.method == "POST":
        form = EmployeeForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("employees:employee_list")

    else:
        form = EmployeeForm()

    context = {"form": form}
    return render(request, "employees/employee_add.html", context)


def employee_edit_view(request, pk):
    employee = get_object_or_404(Employee, pk=pk)

    if request.method == "POST":
        form = EmployeeForm(request.POST, instance=employee)

        if form.is_valid():
            form.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("employees:employee_list")

    form = EmployeeForm(instance=employee)

    context = {"form": form}
    return render(request, "employees/employee_edit.html", context)


def employee_delete_view(request, pk):
    employee = get_object_or_404(Employee, pk=pk)

    if request.method == "POST":
        employee.delete()
        messages.warning(request, "Registro deletado com sucesso")
        return redirect("employees:employee_list")

    form = EmployeeForm(instance=employee)
    for field in form.fields.values():
        field.disabled = True

    context = {"form": form}
    return render(request, "employees/employee_delete.html", context)


# EMPLOYEE_ROLES VIEWS


def employee_role_list_view(request):
    employee_roles = EmployeeRoleType.objects.all()

    context = {"employee_roles": employee_roles}
    return render(request, "employees/employee_role_list.html", context)


def employee_role_add_view(request):
    if request.method == "POST":
        form = EmployeeRoleTypeForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("employees:employee_role_list")

    else:
        form = EmployeeRoleTypeForm()

    context = {"form": form}
    return render(request, "employees/employee_role_add.html", context)


def employee_role_edit_view(request, pk):
    employee_role = get_object_or_404(EmployeeRoleType, pk=pk)

    if request.method == "POST":
        form = EmployeeRoleTypeForm(request.POST, instance=employee_role)

        if form.is_valid():
            form.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("employees:employee_role_list")

    form = EmployeeRoleTypeForm(instance=employee_role)

    context = {"form": form}
    return render(request, "employees/employee_role_edit.html", context)


def employee_role_delete_view(request, pk):
    employee_role = get_object_or_404(EmployeeRoleType, pk=pk)

    if request.method == "POST":
        employee_role.delete()
        messages.warning(request, "Registro deletado com sucesso")
        return redirect("employees:employee_role_list")

    form = EmployeeRoleTypeForm(instance=employee_role)
    for field in form.fields.values():
        field.disabled = True

    context = {"form": form}
    return render(request, "employees/employee_role_delete.html", context)
