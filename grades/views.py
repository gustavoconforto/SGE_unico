from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    UpdateView,
)

from base.search import HtmxSearchMixin
from grades.forms import SubjectForm
from grades.models import Subject


class SubjectListView(HtmxSearchMixin, ListView):
    model = Subject
    template_name = "subjects/subject_list.html"
    context_object_name = "subjects"
    partial_template_name = "subjects/partials/subject_table.html"
    paginate_by = 10
    search_fields = ("name",)


class SubjectCreateView(CreateView):
    model = Subject
    template_name = "subjects/subject_add.html"
    form_class = SubjectForm
    success_url = reverse_lazy("grades:subject_list")


class SubjectUpdateView(UpdateView):
    model = Subject
    template_name = "subjects/subject_edit.html"
    form_class = SubjectForm
    success_url = reverse_lazy("grades:subject_list")


class SubjectDeleteView(DeleteView):
    model = Subject
    template_name = "subjects/subject_delete.html"
    success_url = reverse_lazy("grades:subject_list")
