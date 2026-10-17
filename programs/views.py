from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from programs.forms import ProgramForm
from programs.models import Program


def program_list_view(request):
    programs = Program.objects.all()

    context = {"programs": programs}
    return render(request, "programs/program_list.html", context)


def program_add_view(request):
    if request.method == "POST":
        form = ProgramForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("programs:program_list")

    else:
        form = ProgramForm()

    context = {"form": form}
    return render(request, "programs/program_add.html", context)


def program_edit_view(request, pk):
    program = get_object_or_404(Program, pk=pk)

    if request.method == "POST":
        form = ProgramForm(request.POST, instance=program)

        if form.is_valid():
            form.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("programs:program_list")

    form = ProgramForm(instance=program)

    context = {"form": form}
    return render(request, "programs/program_edit.html", context)


def program_delete_view(request, pk):
    program = get_object_or_404(Program, pk=pk)

    if request.method == "POST":
        program.delete()
        messages.warning(request, "Registro deletado com sucesso")
        return redirect("programs:program_list")

    form = ProgramForm(instance=program)
    for field in form.fields.values():
        field.disabled = True

    context = {"form": form}
    return render(request, "programs/program_delete.html", context)
