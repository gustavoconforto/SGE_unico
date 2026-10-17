from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from base.search import HtmxSearchMixin
from programs.forms import ProgramForm
from programs.models import Program


class ProgramListView(HtmxSearchMixin, ListView):
    model = Program
    template_name = "programs/program_list.html"
    context_object_name = "programs"
    partial_template_name = "programs/partials/program_table.html"
    paginate_by = 10
    ordering = ("name",)
    search_fields = ("name",)


class ProgramCreateView(CreateView):
    model = Program
    template_name = "programs/program_add.html"
    form_class = ProgramForm
    success_url = reverse_lazy("programs:program_list")


class ProgramUpdateView(UpdateView):
    model = Program
    template_name = "programs/program_edit.html"
    form_class = ProgramForm
    success_url = reverse_lazy("programs:program_list")


class ProgramDeleteView(DeleteView):
    model = Program
    template_name = "programs/program_delete.html"
    success_url = reverse_lazy("programs:program_list")
