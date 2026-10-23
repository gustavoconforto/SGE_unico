from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.views import ProtectedDeleteMixin, SuccessMessageMixin
from base.search import HtmxFilterMixin
from q_and_a.forms import QandAFilterForm, QandAForm
from q_and_a.models import QandA


class QandAListView(HtmxFilterMixin, ListView):
    model = QandA
    template_name = "q_and_as/q_and_a_list.html"
    partial_template_name = "q_and_as/partials/q_and_a_table.html"
    context_object_name = "q_and_as"
    paginate_by = 10
    ordering = ("-q_and_a_date", "-created_at")
    search_fields = (
        "enrollment__student__name",
        "enrollment__student__social_name",
        "subject__name",
    )
    filter_form_class = QandAFilterForm
    filter_lookups = {
        "date_from": "q_and_a_date__gte",
        "date_to": "q_and_a_date__lte",
    }

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "enrollment__student", "enrollment__school_class", "subject"
            )
        )


class QandACreateView(SuccessMessageMixin, CreateView):
    model = QandA
    form_class = QandAForm
    template_name = "q_and_as/q_and_a_add.html"
    success_url = reverse_lazy("q_and_a:q_and_a_list")
    success_message = "Registro cadastrado com sucesso"


class QandAUpdateView(SuccessMessageMixin, UpdateView):
    model = QandA
    form_class = QandAForm
    template_name = "q_and_as/q_and_a_edit.html"
    success_url = reverse_lazy("q_and_a:q_and_a_list")
    success_message = "Registro atualizado com sucesso"


class QandADeleteView(ProtectedDeleteMixin, DeleteView):
    model = QandA
    template_name = "q_and_as/q_and_a_delete.html"
    success_url = reverse_lazy("q_and_a:q_and_a_list")
