from django.contrib import messages
from django.contrib.auth.models import Group, Permission, User
from django.shortcuts import get_object_or_404, redirect, render

from base.forms import GroupForm, PermissionForm, UserForm


def main_view(request):
    return render(request, "base/base.html", {})


# USERS VIEWS


def user_list_view(request):
    users = User.objects.all()

    context = {"users": users}
    return render(request, "users/user_list.html", context)


def user_add_view(request):
    if request.method == "POST":
        form = UserForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("base:user_list")

    else:
        form = UserForm()

    context = {"form": form}
    return render(request, "users/user_add.html", context)


def user_edit_view(request, pk):
    user = get_object_or_404(User, pk=pk)

    if request.method == "POST":
        form = UserForm(request.POST, instance=user)

        if form.is_valid():
            form.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("base:user_list")

    form = UserForm(instance=user)

    context = {"form": form}
    return render(request, "users/user_edit.html", context)


def user_delete_view(request, pk):
    user = get_object_or_404(User, pk=pk)

    if request.method == "POST":
        user.delete()
        messages.warning(request, "Registro deletado com sucesso")
        return redirect("base:user_list")

    form = UserForm(instance=user)
    for field in form.fields.values():
        field.disabled = True

    context = {"form": form}
    return render(request, "users/user_delete.html", context)


# GROUPS VIEWS


def group_list_view(request):
    groups = Group.objects.all()

    context = {"groups": groups}
    return render(request, "users/group_list.html", context)


def group_add_view(request):
    if request.method == "POST":
        form = GroupForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("base:group_list")

    else:
        form = GroupForm()

    context = {"form": form}
    return render(request, "users/group_add.html", context)


def group_edit_view(request, pk):
    group = get_object_or_404(Group, pk=pk)

    if request.method == "POST":
        form = GroupForm(request.POST, instance=group)

        if form.is_valid():
            form.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("base:group_list")

    form = GroupForm(instance=group)

    context = {"form": form}
    return render(request, "users/group_edit.html", context)


def group_delete_view(request, pk):
    group = get_object_or_404(Group, pk=pk)

    if request.method == "POST":
        group.delete()
        messages.warning(request, "Registro deletado com sucesso")
        return redirect("base:group_list")

    form = GroupForm(instance=group)
    for field in form.fields.values():
        field.disabled = True

    context = {"form": form}
    return render(request, "users/group_delete.html", context)


# Permissions views


def permission_list_view(request):
    permissions = Permission.objects.all()

    context = {"permissions": permissions}
    return render(request, "users/permission_list.html", context)


def permission_add_view(request):
    if request.method == "POST":
        form = PermissionForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("base:permission_list")

    else:
        form = PermissionForm()

    context = {"form": form}
    return render(request, "users/permission_add.html", context)


def permission_edit_view(request, pk):
    permission = get_object_or_404(Permission, pk=pk)

    if request.method == "POST":
        form = PermissionForm(request.POST, instance=permission)

        if form.is_valid():
            form.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("base:permission_list")

    form = PermissionForm(instance=permission)

    context = {"form": form}
    return render(request, "users/permission_edit.html", context)


def permission_delete_view(request, pk):
    permission = get_object_or_404(Permission, pk=pk)

    if request.method == "POST":
        permission.delete()
        messages.warning(request, "Registro deletado com sucesso")
        return redirect("base:permission_list")

    form = PermissionForm(instance=permission)
    for field in form.fields.values():
        field.disabled = True

    context = {"form": form}
    return render(request, "users/permission_delete.html", context)
