from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from students.forms import GuardianForm, GuardianFormSet, StudentForm
from students.models import Guardian, Student

# GUARDIAN VIEWS


def guardian_list_view(request):
    guardians = Guardian.objects.all()

    context = {"guardians": guardians}
    return render(request, "guardians/guardian_list.html", context)


def guardian_add_view(request):
    if request.method == "POST":
        form = GuardianForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("students:guardian_list")

    else:
        form = GuardianForm()

    context = {"form": form}
    return render(request, "guardians/guardian_add.html", context)


def guardian_edit_view(request, pk):
    guardian = get_object_or_404(Guardian, pk=pk)

    if request.method == "POST":
        form = GuardianForm(request.POST, instance=guardian)

        if form.is_valid():
            form.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("students:guardian_list")

    form = GuardianForm(instance=guardian)

    context = {"form": form}
    return render(request, "guardians/guardian_edit.html", context)


def guardian_delete_view(request, pk):
    guardian = get_object_or_404(Guardian, pk=pk)

    if request.method == "POST":
        guardian.delete()
        messages.warning(request, "Registro deletado com sucesso")
        return redirect("students:guardian_list")

    form = GuardianForm(instance=guardian)
    for field in form.fields.values():
        field.disabled = True

    context = {"form": form}
    return render(request, "guardians/guardian_delete.html", context)


# STUDENT VIEWS


def student_list_view(request):
    students = Student.objects.all()

    context = {"students": students}
    return render(request, "students/student_list.html", context)


def _student_active_tab(form, formset):
    if not form.errors and formset.total_error_count():
        return "guardians"
    return form.active_tab


def student_add_view(request):
    if request.method == "POST":
        form = StudentForm(request.POST, request.FILES)
        formset = GuardianFormSet(request.POST, prefix="guardians")

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                student = form.save()
                formset.instance = student
                formset.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("students:student_list")

    else:
        form = StudentForm()
        formset = GuardianFormSet(prefix="guardians")

    context = {
        "form": form,
        "formset": formset,
        "active_tab": _student_active_tab(form, formset),
    }
    return render(request, "students/student_add.html", context)


def student_edit_view(request, pk):
    student = get_object_or_404(Student, pk=pk)

    if request.method == "POST":
        form = StudentForm(request.POST, request.FILES, instance=student)
        formset = GuardianFormSet(request.POST, instance=student, prefix="guardians")

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("students:student_list")

    else:
        form = StudentForm(instance=student)
        formset = GuardianFormSet(instance=student, prefix="guardians")

    context = {
        "form": form,
        "formset": formset,
        "active_tab": _student_active_tab(form, formset),
    }
    return render(request, "students/student_edit.html", context)


def student_delete_view(request, pk):
    student = get_object_or_404(Student, pk=pk)

    if request.method == "POST":
        student.delete()
        messages.warning(request, "Registro deletado com sucesso")
        return redirect("students:student_list")

    form = StudentForm(instance=student)
    for field in form.fields.values():
        field.disabled = True

    context = {"form": form}
    return render(request, "students/guardian_delete.html", context)
