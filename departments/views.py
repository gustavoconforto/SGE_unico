from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.views import ProtectedDeleteMixin, SuccessMessageMixin
from base.search import HtmxSearchMixin
from departments.forms import DepartmentForm
from departments.models import Department


class DepartmentListView(HtmxSearchMixin, ListView):
    model = Department
    queryset = Department.objects.prefetch_related("teachers", "subjects")
    template_name = "departments/department_list.html"
    partial_template_name = "departments/partials/department_table.html"
    context_object_name = "departments"
    paginate_by = 10
    ordering = ("name",)
    search_fields = ("name", "teachers__name", "subjects__name")

    def get_queryset(self):
        # Searching by teacher or subject joins the related tables.
        return super().get_queryset().distinct()


class DepartmentCreateView(SuccessMessageMixin, CreateView):
    model = Department
    form_class = DepartmentForm
    template_name = "departments/department_add.html"
    success_url = reverse_lazy("departments:department_list")
    success_message = "Registro cadastrado com sucesso"


class DepartmentUpdateView(SuccessMessageMixin, UpdateView):
    model = Department
    form_class = DepartmentForm
    template_name = "departments/department_edit.html"
    success_url = reverse_lazy("departments:department_list")
    success_message = "Registro atualizado com sucesso"


class DepartmentDeleteView(ProtectedDeleteMixin, DeleteView):
    model = Department
    template_name = "departments/department_delete.html"
    success_url = reverse_lazy("departments:department_list")
    protected_message = "Este departamento possui matérias e não pode ser deletado."
