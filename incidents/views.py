from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    UpdateView,
)

from accounts.views import ProtectedDeleteMixin, SuccessMessageMixin
from base.search import HtmxSearchMixin
from incidents.forms import (
    BathroomPermissionForm,
    IncidentForm,
    IncidentTypeForm,
    StudentDelayForm,
)
from incidents.models import BathroomPermission, Incident, IncidentType, StudentDelay

# INCIDENT VIEWS


class IncidentListView(HtmxSearchMixin, ListView):
    model = Incident
    template_name = "incidents/incident_list.html"
    partial_template_name = "incidents/partials/incident_table.html"
    context_object_name = "incidents"
    paginate_by = 10
    ordering = ("-incident_date", "-created_at")
    search_fields = (
        "enrollment__student__name",
        "enrollment__student__social_name",
        "incident_type__type",
    )

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "enrollment__student", "enrollment__school_class", "incident_type"
            )
        )


class IncidentCreateView(SuccessMessageMixin, CreateView):
    model = Incident
    form_class = IncidentForm
    template_name = "incidents/incident_add.html"
    success_url = reverse_lazy("incidents:incident_list")
    success_message = "Registro cadastrado com sucesso"


class IncidentUpdateView(SuccessMessageMixin, UpdateView):
    model = Incident
    form_class = IncidentForm
    template_name = "incidents/incident_edit.html"
    success_url = reverse_lazy("incidents:incident_list")
    success_message = "Registro atualizado com sucesso"


class IncidentDeleteView(ProtectedDeleteMixin, DeleteView):
    model = Incident
    template_name = "incidents/incident_delete.html"
    success_url = reverse_lazy("incidents:incident_list")


# INCIDENT TYPE VIEWS


class IncidentTypeListView(HtmxSearchMixin, ListView):
    model = IncidentType
    template_name = "incident_types/incident_type_list.html"
    partial_template_name = "incident_types/partials/incident_type_table.html"
    context_object_name = "incident_types"
    paginate_by = 10
    ordering = ("type",)
    search_fields = ("type",)


class IncidentTypeCreateView(SuccessMessageMixin, CreateView):
    model = IncidentType
    form_class = IncidentTypeForm
    template_name = "incident_types/incident_type_add.html"
    success_url = reverse_lazy("incidents:incident_type_list")
    success_message = "Registro cadastrado com sucesso"


class IncidentTypeUpdateView(SuccessMessageMixin, UpdateView):
    model = IncidentType
    form_class = IncidentTypeForm
    template_name = "incident_types/incident_type_edit.html"
    success_url = reverse_lazy("incidents:incident_type_list")
    success_message = "Registro atualizado com sucesso"


class IncidentTypeDeleteView(ProtectedDeleteMixin, DeleteView):
    model = IncidentType
    template_name = "incident_types/incident_type_delete.html"
    success_url = reverse_lazy("incidents:incident_type_list")
    protected_message = (
        "Este tipo de ocorrência possui ocorrências e não pode ser deletado."
    )


# STUDENT DELAY VIEWS


class StudentDelayListView(HtmxSearchMixin, ListView):
    model = StudentDelay
    template_name = "student_delays/student_delay_list.html"
    partial_template_name = "student_delays/partials/student_delay_table.html"
    context_object_name = "student_delays"
    paginate_by = 10
    ordering = ("-incident_date", "-created_at")
    search_fields = ("enrollment__student__name", "enrollment__student__social_name")

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("enrollment__student", "enrollment__school_class")
        )


class StudentDelayCreateView(SuccessMessageMixin, CreateView):
    model = StudentDelay
    form_class = StudentDelayForm
    template_name = "student_delays/student_delay_add.html"
    success_url = reverse_lazy("incidents:student_delay_list")
    success_message = "Registro cadastrado com sucesso"


class StudentDelayUpdateView(SuccessMessageMixin, UpdateView):
    model = StudentDelay
    form_class = StudentDelayForm
    template_name = "student_delays/student_delay_edit.html"
    success_url = reverse_lazy("incidents:student_delay_list")
    success_message = "Registro atualizado com sucesso"


class StudentDelayDeleteView(ProtectedDeleteMixin, DeleteView):
    model = StudentDelay
    template_name = "student_delays/student_delay_delete.html"
    success_url = reverse_lazy("incidents:student_delay_list")


# BATHROOM PERMISSION VIEWS


class BathroomPermissionListView(HtmxSearchMixin, ListView):
    model = BathroomPermission
    template_name = "bathroom_permissions/bathroom_permission_list.html"
    partial_template_name = (
        "bathroom_permissions/partials/bathroom_permission_table.html"
    )
    context_object_name = "bathroom_permissions"
    paginate_by = 10
    ordering = ("-incident_date", "-created_at")
    search_fields = ("enrollment__student__name", "enrollment__student__social_name")

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("enrollment__student", "enrollment__school_class")
        )


class BathroomPermissionCreateView(SuccessMessageMixin, CreateView):
    model = BathroomPermission
    form_class = BathroomPermissionForm
    template_name = "bathroom_permissions/bathroom_permission_add.html"
    success_url = reverse_lazy("incidents:bathroom_permission_list")
    success_message = "Registro cadastrado com sucesso"


class BathroomPermissionUpdateView(SuccessMessageMixin, UpdateView):
    model = BathroomPermission
    form_class = BathroomPermissionForm
    template_name = "bathroom_permissions/bathroom_permission_edit.html"
    success_url = reverse_lazy("incidents:bathroom_permission_list")
    success_message = "Registro atualizado com sucesso"


class BathroomPermissionDeleteView(ProtectedDeleteMixin, DeleteView):
    model = BathroomPermission
    template_name = "bathroom_permissions/bathroom_permission_delete.html"
    success_url = reverse_lazy("incidents:bathroom_permission_list")
