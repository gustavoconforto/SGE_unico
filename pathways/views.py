from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.views import ProtectedDeleteMixin, SuccessMessageMixin
from base.search import HtmxFilterMixin, HtmxSearchMixin, is_htmx_partial
from classes.views import get_int_param
from enrollments.models import SchoolYear
from incidents.views import IncidentGradesAll, IncidentGradesIndividual
from pathways.forms import (
    AttendanceSheetForm,
    ExtraGradeSettingsForm,
    PathwayEnrollmentFilterForm,
    PathwayEnrollmentForm,
    PathwayForm,
    PathwayGradeSelectForm,
    PathwayGradeSheetForm,
    PathwayOfferingFilterForm,
    PathwayOfferingForm,
    PathwaySessionFilterForm,
    PathwaySessionForm,
)
from pathways.models import (
    AttendanceStatus,
    ExtraGradeSettings,
    Pathway,
    PathwayEnrollment,
    PathwayOffering,
    PathwaySession,
)
from pathways.services import EXTRA_CODE, extra_exam_type, save_extra_grades


def list_url(name, offering_id):
    """The list `name`, filtered by the offering when there is one."""
    url = reverse(name)
    return f"{url}?offering={offering_id}" if offering_id else url


class OfferingInitialMixin:
    """Prefill the offering from ?offering=<pk>, for links from the offering list."""

    def get_initial(self):
        return {
            **super().get_initial(),
            "offering": get_int_param(self.request, "offering"),
        }


# PATHWAY VIEWS


class PathwayListView(HtmxSearchMixin, ListView):
    model = Pathway
    template_name = "pathways/pathway_list.html"
    partial_template_name = "pathways/partials/pathway_table.html"
    context_object_name = "pathways"
    paginate_by = 10
    ordering = ("name",)
    search_fields = ("name", "description")


class PathwayCreateView(SuccessMessageMixin, CreateView):
    model = Pathway
    form_class = PathwayForm
    template_name = "pathways/pathway_add.html"
    success_url = reverse_lazy("pathways:pathway_list")
    success_message = "Registro cadastrado com sucesso"


class PathwayUpdateView(SuccessMessageMixin, UpdateView):
    model = Pathway
    form_class = PathwayForm
    template_name = "pathways/pathway_edit.html"
    success_url = reverse_lazy("pathways:pathway_list")
    success_message = "Registro atualizado com sucesso"


class PathwayDeleteView(ProtectedDeleteMixin, DeleteView):
    model = Pathway
    template_name = "pathways/pathway_delete.html"
    success_url = reverse_lazy("pathways:pathway_list")
    protected_message = "Este itinerário possui turmas e não pode ser deletado."


# PATHWAY OFFERING VIEWS


class PathwayOfferingListView(HtmxFilterMixin, ListView):
    model = PathwayOffering
    template_name = "pathway_offerings/pathway_offering_list.html"
    partial_template_name = "pathway_offerings/partials/pathway_offering_table.html"
    context_object_name = "offerings"
    paginate_by = 10
    ordering = ("-school_year__begins", "pathway__name", "name")
    search_fields = ("pathway__name", "name", "schedule", "teachers__name")
    filter_form_class = PathwayOfferingFilterForm

    def get_queryset(self):
        # Searching by teacher joins the many-to-many table.
        return (
            super()
            .get_queryset()
            .select_related("pathway", "school_year")
            .prefetch_related("teachers")
            .annotate(
                members=Count(
                    "pathway_enrollments",
                    filter=Q(pathway_enrollments__left_at__isnull=True),
                    distinct=True,
                )
            )
            .distinct()
        )


class PathwayOfferingCreateView(SuccessMessageMixin, CreateView):
    model = PathwayOffering
    form_class = PathwayOfferingForm
    template_name = "pathway_offerings/pathway_offering_add.html"
    success_url = reverse_lazy("pathways:pathway_offering_list")
    success_message = "Registro cadastrado com sucesso"


class PathwayOfferingUpdateView(SuccessMessageMixin, UpdateView):
    model = PathwayOffering
    form_class = PathwayOfferingForm
    template_name = "pathway_offerings/pathway_offering_edit.html"
    success_url = reverse_lazy("pathways:pathway_offering_list")
    success_message = "Registro atualizado com sucesso"


class PathwayOfferingDeleteView(ProtectedDeleteMixin, DeleteView):
    model = PathwayOffering
    template_name = "pathway_offerings/pathway_offering_delete.html"
    success_url = reverse_lazy("pathways:pathway_offering_list")
    protected_message = (
        "Esta turma de itinerário possui inscrições ou aulas e não pode ser deletada."
    )


# PATHWAY ENROLLMENT VIEWS


class PathwayEnrollmentListView(HtmxFilterMixin, ListView):
    model = PathwayEnrollment
    template_name = "pathway_enrollments/pathway_enrollment_list.html"
    partial_template_name = "pathway_enrollments/partials/pathway_enrollment_table.html"
    context_object_name = "pathway_enrollments"
    paginate_by = 10
    ordering = ("offering__pathway__name", "enrollment__student__name")
    search_fields = (
        "enrollment__student__name",
        "enrollment__student__social_name",
        "offering__pathway__name",
    )
    filter_form_class = PathwayEnrollmentFilterForm

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "enrollment__student",
                "enrollment__school_class",
                "offering__pathway",
                "offering__school_year",
            )
        )

    def filter_status(self, queryset, value):
        return queryset.filter(left_at__isnull=value == "current")


class PathwayEnrollmentSuccessMixin:
    def get_success_url(self):
        return list_url("pathways:pathway_enrollment_list", self.object.offering_id)


class PathwayEnrollmentCreateView(
    PathwayEnrollmentSuccessMixin,
    OfferingInitialMixin,
    SuccessMessageMixin,
    CreateView,
):
    model = PathwayEnrollment
    form_class = PathwayEnrollmentForm
    template_name = "pathway_enrollments/pathway_enrollment_add.html"
    success_message = "Registro cadastrado com sucesso"


class PathwayEnrollmentUpdateView(
    PathwayEnrollmentSuccessMixin, SuccessMessageMixin, UpdateView
):
    model = PathwayEnrollment
    form_class = PathwayEnrollmentForm
    template_name = "pathway_enrollments/pathway_enrollment_edit.html"
    success_message = "Registro atualizado com sucesso"


class PathwayEnrollmentDeleteView(
    PathwayEnrollmentSuccessMixin, ProtectedDeleteMixin, DeleteView
):
    model = PathwayEnrollment
    template_name = "pathway_enrollments/pathway_enrollment_delete.html"
    protected_message = (
        "Este aluno possui presenças ou notas no itinerário e não pode ser "
        "deletado. Registre a data de saída."
    )


# PATHWAY SESSION VIEWS


class PathwaySessionListView(HtmxFilterMixin, ListView):
    model = PathwaySession
    template_name = "pathway_sessions/pathway_session_list.html"
    partial_template_name = "pathway_sessions/partials/pathway_session_table.html"
    context_object_name = "sessions"
    paginate_by = 10
    ordering = ("-date", "offering__pathway__name")
    search_fields = ("offering__pathway__name", "offering__name", "topic")
    filter_form_class = PathwaySessionFilterForm
    filter_lookups = {"date_from": "date__gte", "date_to": "date__lte"}

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("offering__pathway", "offering__school_year")
            .annotate(
                present=Count(
                    "attendances",
                    filter=Q(attendances__status=AttendanceStatus.PRESENT),
                ),
                absent=Count(
                    "attendances",
                    filter=~Q(attendances__status=AttendanceStatus.PRESENT),
                ),
            )
        )


class PathwaySessionCreateView(OfferingInitialMixin, SuccessMessageMixin, CreateView):
    """Create the lesson, then take its roll call."""

    model = PathwaySession
    form_class = PathwaySessionForm
    template_name = "pathway_sessions/pathway_session_add.html"
    success_message = "Registro cadastrado com sucesso"

    def get_success_url(self):
        return reverse("pathways:pathway_session_attendance", args=[self.object.pk])


class PathwaySessionUpdateView(SuccessMessageMixin, UpdateView):
    model = PathwaySession
    form_class = PathwaySessionForm
    template_name = "pathway_sessions/pathway_session_edit.html"
    success_message = "Registro atualizado com sucesso"

    def get_success_url(self):
        return list_url("pathways:pathway_session_list", self.object.offering_id)


class PathwaySessionDeleteView(ProtectedDeleteMixin, DeleteView):
    model = PathwaySession
    template_name = "pathway_sessions/pathway_session_delete.html"

    def get_success_url(self):
        return list_url("pathways:pathway_session_list", self.object.offering_id)


class PathwaySessionAttendanceView(TemplateView):
    """Roll call of a lesson; saving records every student's status."""

    template_name = "pathway_sessions/pathway_session_attendance.html"

    def dispatch(self, request, *args, **kwargs):
        self.session = get_object_or_404(
            PathwaySession.objects.select_related(
                "offering__pathway", "offering__school_year"
            ),
            pk=kwargs["pk"],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["session"] = self.session
        context.setdefault("form", AttendanceSheetForm(session=self.session))
        return context

    def post(self, request, *args, **kwargs):
        form = AttendanceSheetForm(request.POST, session=self.session)
        if form.is_valid():
            form.save()
            messages.success(request, "Registro atualizado com sucesso")
            return redirect(
                list_url("pathways:pathway_session_list", self.session.offering_id)
            )
        return self.render_to_response(self.get_context_data(form=form))


# PATHWAY GRADE VIEWS


class PathwayGradeEntryView(TemplateView):
    """Grade sheet of the offering and bimester picked in the query string."""

    template_name = "pathway_grades/pathway_grade_entry.html"
    partial_template_name = "pathway_grades/partials/pathway_grade_sheet.html"

    def get_template_names(self):
        if is_htmx_partial(self.request):
            return [self.partial_template_name]
        return [self.template_name]

    def get_sheet_form(self, data=None):
        select_form = PathwayGradeSelectForm(self.request.GET or None)
        if not (select_form.is_valid() and all(select_form.cleaned_data.values())):
            return select_form, None
        return select_form, PathwayGradeSheetForm(
            data,
            offering=select_form.cleaned_data["offering"],
            bimester=select_form.cleaned_data["bimester"],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        select_form, sheet = self.get_sheet_form()
        context["select_form"] = select_form
        context.setdefault("form", sheet)
        return context

    def post(self, request, *args, **kwargs):
        _, form = self.get_sheet_form(request.POST)
        if form is None:
            return redirect(request.get_full_path())
        if form.is_valid():
            form.save()
            messages.success(request, "Registro atualizado com sucesso")
            return redirect(request.get_full_path())
        messages.error(request, "Corrija as notas destacadas. Nenhuma nota foi salva.")
        return self.render_to_response(self.get_context_data(form=form))


# EXTRA GRADE VIEWS

EXTRA_MISSING = (
    f"Cadastre o tipo de avaliação Nota extra (sigla {EXTRA_CODE}) para calcular."
)


class ExtraGradeMixin:
    """The concept grade screens, calculating the extra grade instead."""

    exam_type_missing = EXTRA_MISSING

    def get_exam_type(self):
        return extra_exam_type()

    def save_grades(self, enrollments, bimester, exam_type):
        return save_extra_grades(enrollments, bimester, exam_type)


class ExtraGradesIndividual(ExtraGradeMixin, IncidentGradesIndividual):
    template_name = "extra_grades/extra_grades_individual.html"
    partial_template_name = "extra_grades/partials/extra_grades_subjects.html"


class ExtraGradesAll(ExtraGradeMixin, IncidentGradesAll):
    template_name = "extra_grades/extra_grades_all.html"
    partial_template_name = "extra_grades/partials/extra_grades_table.html"
    url_name = "pathways:extra_grades_all"


# EXTRA GRADE SETTINGS VIEWS


class ExtraGradeSettingsListView(HtmxSearchMixin, ListView):
    """School years with their extra grade rules; a year without settings
    shows the defaults it will get on first use."""

    model = SchoolYear
    template_name = "extra_grade_settings/extra_grade_settings_list.html"
    partial_template_name = (
        "extra_grade_settings/partials/extra_grade_settings_table.html"
    )
    context_object_name = "school_years"
    paginate_by = 10
    ordering = ("-begins",)
    search_fields = ("begins", "ends")

    def get_queryset(self):
        return super().get_queryset().select_related("extra_grade_settings")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["defaults"] = ExtraGradeSettings()
        return context


class ExtraGradeSettingsUpdateView(SuccessMessageMixin, UpdateView):
    model = ExtraGradeSettings
    form_class = ExtraGradeSettingsForm
    template_name = "extra_grade_settings/extra_grade_settings_edit.html"
    success_url = reverse_lazy("pathways:extra_grade_settings_list")
    success_message = "Registro atualizado com sucesso"

    def get_object(self, queryset=None):
        school_year = get_object_or_404(SchoolYear, pk=self.kwargs["school_year_pk"])
        return ExtraGradeSettings.for_school_year(school_year)
