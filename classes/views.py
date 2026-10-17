from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    UpdateView,
)

from base.search import HtmxSearchMixin
from classes.forms import ClassForm
from classes.models import Class


class ClassListView(HtmxSearchMixin, ListView):
    model = Class
    template_name = "classes/class_list.html"
    context_object_name = "classes"
    partial_template_name = "classes/partials/class_table.html"
    paginate_by = 10
    ordering = ("-year__begins", "program__name", "grade_level", "name")
    search_fields = ("name", "program__name", "year__begins")


class ClassCreateView(CreateView):
    model = Class
    template_name = "classes/class_add.html"
    form_class = ClassForm
    success_url = reverse_lazy("classes:class_list")


class ClassUpdateView(UpdateView):
    model = Class
    template_name = "classes/class_edit.html"
    form_class = ClassForm
    success_url = reverse_lazy("classes:class_list")


class ClassDeleteView(DeleteView):
    model = Class
    template_name = "classes/class_delete.html"
    success_url = reverse_lazy("classes:class_list")
