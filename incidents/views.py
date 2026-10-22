from django.contrib import messages
from django.db.models import Max, Min
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.views import ProtectedDeleteMixin, SuccessMessageMixin
from base.search import HtmxSearchMixin, apply_search, is_htmx_partial
from grades.models import Grade, GradeLevelSubject
from incidents.forms import (
    BathroomPermissionForm,
    ConceptBimesterFilterForm,
    ConceptGradeForm,
    IncidentForm,
    IncidentTypeForm,
    StudentDelayForm,
    active_enrollments,
)
from incidents.models import BathroomPermission, Incident, IncidentType, StudentDelay
from incidents.services import (
    CONCEPT_CODE,
    bimester_range,
    concept_exam_type,
    save_concept_grades,
)

# INCIDENT GRADES

CONCEPT_MISSING = (
    f"Cadastre o tipo de avaliação Conceito (sigla {CONCEPT_CODE}) para calcular."
)


class IncidentGradesIndividual(TemplateView):
    """Concept grade of every subject for the enrollment and bimester picked in
    the query string; POST recomputes it from incidents and delays."""

    template_name = "incident_grades/incident_grades_individual.html"
    partial_template_name = "incident_grades/partials/incident_grades_subjects.html"

    def get_template_names(self):
        if is_htmx_partial(self.request):
            return [self.partial_template_name]
        return [self.template_name]

    def get_selection(self):
        form = ConceptGradeForm(self.request.GET or None)
        if form.is_valid() and all(form.cleaned_data.values()):
            return form, form.cleaned_data["enrollment"], form.cleaned_data["bimester"]
        return form, None, None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form, enrollment, bimester = self.get_selection()
        exam_type = concept_exam_type()
        context.update(form=form, enrollment=enrollment, exam_type=exam_type)
        if enrollment is None:
            return context
        school_class = enrollment.school_class
        level_subjects = (
            GradeLevelSubject.objects.filter(grade_level=school_class.grade_level)
            .select_related("subject")
            .order_by("subject__name")
            if school_class and school_class.grade_level
            else []
        )
        scores = (
            dict(
                Grade.objects.filter(
                    enrollment=enrollment, exam_type=exam_type, bimester=bimester
                ).values_list("subject_id", "score")
            )
            if exam_type
            else {}
        )
        context["rows"] = [
            (item.subject, scores.get(item.subject_id)) for item in level_subjects
        ]
        context["has_dates"] = (
            bimester_range(enrollment.enrollment_type.school_year, bimester) is not None
        )
        return context

    def post(self, request, *args, **kwargs):
        _, enrollment, bimester = self.get_selection()
        exam_type = concept_exam_type()
        if enrollment is None:
            messages.error(request, "Selecione um aluno e um bimestre.")
        elif exam_type is None:
            messages.error(request, CONCEPT_MISSING)
        elif save_concept_grades([enrollment], bimester, exam_type):
            messages.success(request, "Registro atualizado com sucesso")
        else:
            messages.error(
                request,
                "Não foi possível calcular: verifique as datas do bimestre no "
                "ano letivo e as matérias da série do aluno.",
            )
        return redirect(request.get_full_path())


class IncidentGradesAll(HtmxSearchMixin, ListView):
    """Concept grades of the active enrollments for ?bimester; POST recomputes
    them for every active enrollment."""

    template_name = "incident_grades/incident_grades_all.html"
    partial_template_name = "incident_grades/partials/incident_grades_table.html"
    context_object_name = "enrollments"
    paginate_by = 10
    search_fields = ("student__name", "student__social_name", "school_class__name")

    def get_queryset(self):
        return apply_search(
            active_enrollments(), self.get_search_query(), self.search_fields
        )

    def get_bimester(self, data):
        form = ConceptBimesterFilterForm(data or None)
        return form, form.cleaned_data["bimester"] if form.is_valid() else None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form, bimester = self.get_bimester(self.request.GET)
        exam_type = concept_exam_type()
        context.update(filter_form=form, bimester=bimester, exam_type=exam_type)
        enrollments = context["enrollments"]
        ranges = {}
        if bimester and exam_type:
            # Lowest and highest concept grade among the subjects: equal unless
            # some subject was edited by hand.
            ranges = {
                pk: (low, high)
                for pk, low, high in Grade.objects.filter(
                    enrollment_id__in=[item.pk for item in enrollments],
                    exam_type=exam_type,
                    bimester=bimester,
                )
                .order_by()
                .values("enrollment")
                .annotate(low=Min("score"), high=Max("score"))
                .values_list("enrollment", "low", "high")
            }
        for enrollment in enrollments:
            enrollment.concept_range = ranges.get(enrollment.pk)
        return context

    def post(self, request, *args, **kwargs):
        _, bimester = self.get_bimester(request.POST)
        exam_type = concept_exam_type()
        url = reverse("incidents:incident_grades_all")
        if bimester is None:
            messages.error(request, "Selecione um bimestre.")
            return redirect(url)
        if exam_type is None:
            messages.error(request, CONCEPT_MISSING)
        else:
            enrollments = list(active_enrollments())
            graded = save_concept_grades(enrollments, bimester, exam_type)
            messages.success(request, "Registro atualizado com sucesso")
            if skipped := len(enrollments) - graded:
                messages.warning(
                    request,
                    f"{skipped} matrícula(s) sem nota: ano letivo sem as datas do "
                    "bimestre ou turma sem matérias.",
                )
        return redirect(f"{url}?bimester={bimester}")


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
