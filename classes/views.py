from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    UpdateView,
)

from classes.forms import ClassForm
from classes.models import Class


class ClassListView(ListView):
    model = Class
    template_name = "classes/class_list.html"
    context_object_name = "classes"
    paginate_by = 10


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
