from collections import defaultdict

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.views import ProtectedDeleteMixin, SuccessMessageMixin
from base.search import HtmxFilterMixin, HtmxSearchMixin, is_htmx_partial
from classes.views import get_int_param
from enrollments.models import SchoolYear
from grades.models import Bimester
from incidents.forms import ConceptGradeForm, current_school_year
from incidents.services import bimester_range
from incidents.views import IncidentGradesAll, IncidentGradesIndividual
from pathways.forms import (
    AttendanceSheetForm,
    PathwayEnrollmentFilterForm,
    PathwayEnrollmentForm,
    PathwayForm,
    PathwayGradeSelectForm,
    PathwayGradeSheetForm,
    PathwayOfferingFilterForm,
    PathwayOfferingForm,
    PathwaySessionFilterForm,
    PathwaySessionForm,
    SchoolYearSelectForm,
    StudentPathwaysForm,
    StudentPathwaysSelectForm,
    members_between,
)
from pathways.models import (
    AttendanceStatus,
    Pathway,
    PathwayAttendance,
    PathwayEnrollment,
    PathwayOffering,
    PathwaySession,
)
from pathways.services import (
    EXTRA_CODE,
    extra_exam_type,
    lesson_days,
    save_extra_grades,
    with_attendance,
)


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


class PathwayDiaryView(DetailView):
    """Printable attendance diary of an offering in a bimester (?bimester=N):
    a row per student, a column per lesson day."""

    model = PathwayOffering
    template_name = "pathway_offerings/pathway_offering_diary.html"
    context_object_name = "offering"
    queryset = PathwayOffering.objects.select_related(
        "pathway", "school_year"
    ).prefetch_related("teachers")

    def get_bimester(self, school_year):
        bimester = get_int_param(self.request, "bimester")
        if bimester in Bimester.values:
            return bimester
        today = timezone.localdate()
        for value in Bimester.values:
            date_range = bimester_range(school_year, value)
            if date_range and date_range[0] <= today <= date_range[1]:
                return value
        return Bimester.values[0]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        offering = self.object
        bimester = self.get_bimester(offering.school_year)
        date_range = bimester_range(offering.school_year, bimester)
        days = lesson_days(offering, *date_range) if date_range else []
        rows = []
        if days:
            for member in members_between(offering, *date_range):
                rows.append((member, [member.is_member_on(day) for day in days]))
        context.update(
            bimester=bimester,
            bimesters=Bimester.choices,
            date_range=date_range,
            days=days,
            rows=rows,
        )
        return context


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


class PathwayEnrollmentByStudentView(TemplateView):
    """The pathways of the enrollment picked in the query string, to sign the
    student up for several at once."""

    template_name = "pathway_enrollments/pathway_enrollment_by_student.html"
    partial_template_name = (
        "pathway_enrollments/partials/pathway_enrollment_by_student_sheet.html"
    )

    def get_template_names(self):
        if is_htmx_partial(self.request):
            return [self.partial_template_name]
        return [self.template_name]

    def get_sheet_form(self, data=None):
        select_form = StudentPathwaysSelectForm(self.request.GET or None)
        if not (select_form.is_valid() and select_form.cleaned_data["enrollment"]):
            return select_form, None
        return select_form, StudentPathwaysForm(
            data, enrollment=select_form.cleaned_data["enrollment"]
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
        messages.error(request, "Corrija os itinerários destacados. Nada foi salvo.")
        return self.render_to_response(self.get_context_data(form=form))


class StudentAttendanceView(TemplateView):
    """Lessons attended and missed, with the days missed, in every pathway of
    the enrollment and bimester picked in the query string."""

    template_name = "pathway_attendance/student_attendance.html"
    partial_template_name = "pathway_attendance/partials/student_attendance_table.html"

    def get_template_names(self):
        if is_htmx_partial(self.request):
            return [self.partial_template_name]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = ConceptGradeForm(self.request.GET or None)
        context["form"] = form
        if not (form.is_valid() and all(form.cleaned_data.values())):
            return context
        enrollment = form.cleaned_data["enrollment"]
        date_range = bimester_range(
            enrollment.enrollment_type.school_year, form.cleaned_data["bimester"]
        )
        context.update(enrollment=enrollment, date_range=date_range)
        if date_range is None:
            return context
        begins, ends = date_range
        rows = list(
            with_attendance(
                enrollment.pathway_enrollments.filter(joined_at__lte=ends)
                .filter(Q(left_at__isnull=True) | Q(left_at__gte=begins))
                .select_related("offering__pathway", "offering__school_year")
                .order_by("offering__pathway__name", "offering__name"),
                date_range,
            )
        )
        days = defaultdict(lambda: defaultdict(list))
        for member_id, status, day in (
            PathwayAttendance.objects.filter(
                pathway_enrollment__in=rows,
                status__in=[AttendanceStatus.ABSENT, AttendanceStatus.EXCUSED],
                session__date__range=date_range,
            )
            .order_by("session__date")
            .values_list("pathway_enrollment_id", "status", "session__date")
        ):
            days[member_id][status].append(day)
        for row in rows:
            row.absent_days = days[row.pk][AttendanceStatus.ABSENT]
            row.excused_days = days[row.pk][AttendanceStatus.EXCUSED]
        context["rows"] = rows
        return context


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


class PathwayGradeOptionsView(TemplateView):
    """htmx endpoint: the offering select filtered by ?school_year=<pk>."""

    template_name = "pathway_grades/partials/offering_select.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            select_form=PathwayGradeSelectForm(self.request.GET),
            clear_results=True,
            **kwargs,
        )

    def render_to_response(self, context, **kwargs):
        response = super().render_to_response(context, **kwargs)
        # Keep the chosen year in the address bar so a reload restores it.
        response["HX-Push-Url"] = (
            f"{reverse('pathways:pathway_grade_entry')}?{self.request.GET.urlencode()}"
        )
        return response


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

    def get_school_year(self, data):
        if "school_year" not in data:
            return (
                current_school_year() or SchoolYear.objects.order_by("-begins").first()
            )
        form = SchoolYearSelectForm(data)
        return form.cleaned_data["school_year"] if form.is_valid() else None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["year_form"] = SchoolYearSelectForm(
            initial={"school_year": self.school_year}
        )
        return context
