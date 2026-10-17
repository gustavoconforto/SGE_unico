from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from students.forms import GuardianForm, GuardianFormSet, StudentForm
from students.models import Guardian, Student

# GUARDIAN VIEWS


class GuardianListView(ListView):
    model = Guardian
    template_name = "guardians/guardian_list.html"
    context_object_name = "guardians"
    paginate_by = 10


class GuardianCreateView(CreateView):
    model = Guardian
    template_name = "guardians/guardian_add.html"
    form_class = GuardianForm
    success_url = reverse_lazy("guardians:guardian_list")


class GuardianUpdateView(UpdateView):
    model = Guardian
    template_name = "guardians/guardian_edit.html"
    form_class = GuardianForm
    success_url = reverse_lazy("guardians:guardian_list")


# STUDENT VIEWS


class StudentListView(ListView):
    model = Student
    template_name = "students/student_list.html"
    context_object_name = "students"
    paginate_by = 10


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
