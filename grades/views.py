from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy
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
from classes.views import classes_of_year, get_int_param
from enrollments.models import Enrollment, EnrollmentStatus, SchoolYear
from grades.forms import (
    ExamTypeForm,
    GradeLevelSubjectFilterForm,
    GradeLevelSubjectForm,
    GradeSheetForm,
    StudentGradesForm,
    StudentSubjectGradesForm,
    SubjectForm,
)
from grades.models import (
    FINAL_RECOVERY,
    GRADE_PERIODS,
    Bimester,
    ExamKind,
    ExamType,
    GradeLevelSubject,
    Subject,
)
from grades.services import report_card
from incidents.forms import active_enrollments


class SubjectListView(HtmxSearchMixin, ListView):
    model = Subject
    queryset = Subject.objects.select_related("department")
    template_name = "subjects/subject_list.html"
    context_object_name = "subjects"
    partial_template_name = "subjects/partials/subject_table.html"
    paginate_by = 10
    search_fields = ("name", "department__name")


class SubjectCreateView(SuccessMessageMixin, CreateView):
    model = Subject
    template_name = "subjects/subject_add.html"
    form_class = SubjectForm
    success_url = reverse_lazy("grades:subject_list")
    success_message = "Registro cadastrado com sucesso"


class SubjectUpdateView(SuccessMessageMixin, UpdateView):
    model = Subject
    template_name = "subjects/subject_edit.html"
    form_class = SubjectForm
    success_url = reverse_lazy("grades:subject_list")
    success_message = "Registro atualizado com sucesso"


class SubjectDeleteView(ProtectedDeleteMixin, DeleteView):
    model = Subject
    template_name = "subjects/subject_delete.html"
    success_url = reverse_lazy("grades:subject_list")


# EXAM TYPE VIEWS


class ExamTypeListView(HtmxSearchMixin, ListView):
    model = ExamType
    template_name = "exam_types/exam_type_list.html"
    partial_template_name = "exam_types/partials/exam_type_table.html"
    context_object_name = "exam_types"
    paginate_by = 10
    ordering = ("order", "name")
    search_fields = ("name", "code")


class ExamTypeCreateView(SuccessMessageMixin, CreateView):
    model = ExamType
    form_class = ExamTypeForm
    template_name = "exam_types/exam_type_add.html"
    success_url = reverse_lazy("grades:exam_type_list")
    success_message = "Registro cadastrado com sucesso"


class ExamTypeUpdateView(SuccessMessageMixin, UpdateView):
    model = ExamType
    form_class = ExamTypeForm
    template_name = "exam_types/exam_type_edit.html"
    success_url = reverse_lazy("grades:exam_type_list")
    success_message = "Registro atualizado com sucesso"


class ExamTypeDeleteView(ProtectedDeleteMixin, DeleteView):
    model = ExamType
    template_name = "exam_types/exam_type_delete.html"
    success_url = reverse_lazy("grades:exam_type_list")
    protected_message = "Este tipo de avaliação possui notas e não pode ser deletado."


# GRADE LEVEL SUBJECT VIEWS


class GradeLevelSubjectListView(HtmxFilterMixin, ListView):
    model = GradeLevelSubject
    queryset = GradeLevelSubject.objects.select_related("subject").prefetch_related(
        "teachers"
    )
    template_name = "grade_level_subjects/grade_level_subject_list.html"
    partial_template_name = (
        "grade_level_subjects/partials/grade_level_subject_table.html"
    )
    context_object_name = "grade_level_subjects"
    paginate_by = 10
    ordering = ("grade_level", "subject__name")
    search_fields = ("subject__name", "teachers__name")
    filter_form_class = GradeLevelSubjectFilterForm

    def get_queryset(self):
        # Searching by teacher joins the many-to-many table.
        return super().get_queryset().distinct()


class GradeLevelSubjectCreateView(SuccessMessageMixin, CreateView):
    model = GradeLevelSubject
    form_class = GradeLevelSubjectForm
    template_name = "grade_level_subjects/grade_level_subject_add.html"
    success_url = reverse_lazy("grades:grade_level_subject_list")
    success_message = "Registro cadastrado com sucesso"

    def get_initial(self):
        return {
            **super().get_initial(),
            "grade_level": get_int_param(self.request, "grade_level"),
        }


class GradeLevelSubjectUpdateView(SuccessMessageMixin, UpdateView):
    model = GradeLevelSubject
    form_class = GradeLevelSubjectForm
    template_name = "grade_level_subjects/grade_level_subject_edit.html"
    success_url = reverse_lazy("grades:grade_level_subject_list")
    success_message = "Registro atualizado com sucesso"


class GradeLevelSubjectTeachersView(TemplateView):
    """htmx endpoint: the teacher checkboxes for ?subject=<pk>, keeping ?teachers."""

    template_name = "grade_level_subjects/partials/teachers_field.html"

    def get_context_data(self, **kwargs):
        form = GradeLevelSubjectForm(
            initial={
                "subject": get_int_param(self.request, "subject"),
                "teachers": self.request.GET.getlist("teachers"),
            }
        )
        return super().get_context_data(form=form, **kwargs)


class GradeLevelSubjectDeleteView(ProtectedDeleteMixin, DeleteView):
    model = GradeLevelSubject
    template_name = "grade_level_subjects/grade_level_subject_delete.html"
    success_url = reverse_lazy("grades:grade_level_subject_list")


# GRADE ENTRY VIEWS


def grade_selection(request):
    """The year → class → subject → bimester (or final recovery) choices in the
    query string.

    A choice that doesn't belong to the one before it (the class of another
    year, after the year changed) is dropped.
    """
    year_id = get_int_param(request, "school_year")
    class_id = get_int_param(request, "school_class")
    subject_id = get_int_param(request, "subject")
    bimester = get_int_param(request, "bimester")
    classes = classes_of_year(year_id)
    school_class = next((item for item in classes if item.pk == class_id), None)
    level_subjects = (
        GradeLevelSubject.objects.select_related("subject").filter(
            grade_level=school_class.grade_level
        )
        if school_class and school_class.grade_level
        else GradeLevelSubject.objects.none()
    )
    if subject_id not in {item.subject_id for item in level_subjects}:
        subject_id = None
    return {
        "school_years": SchoolYear.objects.order_by("-begins"),
        "classes": classes,
        "level_subjects": level_subjects,
        "bimesters": GRADE_PERIODS,
        "selected_year_id": year_id,
        "selected_class_id": school_class.pk if school_class else None,
        "selected_subject_id": subject_id,
        "selected_bimester": bimester if bimester in dict(GRADE_PERIODS) else None,
    }


class GradeEntryView(TemplateView):
    """Grade sheet of the class, subject and bimester picked in the query string."""

    template_name = "grade_entry/grade_entry.html"
    partial_template_name = "grade_entry/partials/grade_sheet.html"

    def get_template_names(self):
        if is_htmx_partial(self.request):
            return [self.partial_template_name]
        return [self.template_name]

    def get_sheet_form(self, data=None):
        selection = grade_selection(self.request)
        level_subject = next(
            (
                item
                for item in selection["level_subjects"]
                if item.subject_id == selection["selected_subject_id"]
            ),
            None,
        )
        if level_subject is None or selection["selected_bimester"] is None:
            return None
        enrollments = (
            Enrollment.objects.filter(
                school_class_id=selection["selected_class_id"],
                status=EnrollmentStatus.ACTIVE,
            )
            .select_related("student")
            .order_by("student__name")
        )
        # Recovery exams are only taken in the final recovery, and only there.
        exam_types = (
            ExamType.objects.filter(kind=ExamKind.RECOVERY)
            if selection["selected_bimester"] == FINAL_RECOVERY
            else ExamType.objects.exclude(kind=ExamKind.RECOVERY)
        )
        return GradeSheetForm(
            data,
            enrollments=enrollments,
            exam_types=exam_types,
            subject=level_subject.subject,
            bimester=selection["selected_bimester"],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(grade_selection(self.request))
        context.setdefault("form", self.get_sheet_form())
        return context

    def post(self, request, *args, **kwargs):
        form = self.get_sheet_form(request.POST)
        if form is None:
            return redirect(request.get_full_path())
        if form.is_valid():
            form.save()
            messages.success(request, "Registro atualizado com sucesso")
            return redirect(request.get_full_path())
        messages.error(request, "Corrija as notas destacadas. Nenhuma nota foi salva.")
        return self.render_to_response(self.get_context_data(form=form))


class GradeEntrySpecific(TemplateView):
    """Every grade of the active enrollment picked in the query string: each
    exam's score per bimester, the bimester grades, the annual average, the
    recovery and the final grade of every subject."""

    template_name = "student_grades/student_grades.html"
    partial_template_name = "student_grades/partials/student_grades_table.html"

    def get_template_names(self):
        if is_htmx_partial(self.request):
            return [self.partial_template_name]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = StudentGradesForm(self.request.GET or None)
        enrollment = form.cleaned_data["enrollment"] if form.is_valid() else None
        context.update(form=form, enrollment=enrollment)
        if enrollment is None:
            return context
        # Recovery isn't taken in the bimesters: it has its own column.
        exam_types = list(ExamType.objects.exclude(kind=ExamKind.RECOVERY))
        context.update(
            exam_types=exam_types,
            rows=report_card(enrollment, exam_types),
            bimesters=Bimester.choices,
            # Subject, each bimester's exams and grade, the 4 final columns and
            # the actions.
            column_count=1 + len(Bimester) * (len(exam_types) + 1) + 5,
        )
        return context


class StudentGradesRowView(TemplateView):
    """htmx endpoint: one subject's row of the student grades page, read-only."""

    template_name = "student_grades/partials/student_grades_row.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.enrollment = get_object_or_404(
            active_enrollments(), pk=kwargs["enrollment_pk"]
        )
        school_class = self.enrollment.school_class
        self.subject = get_object_or_404(
            GradeLevelSubject.objects.select_related("subject"),
            grade_level=school_class.grade_level if school_class else None,
            subject_id=kwargs["subject_pk"],
        ).subject
        self.exam_types = list(ExamType.objects.exclude(kind=ExamKind.RECOVERY))

    def get_context_data(self, **kwargs):
        row = next(
            item
            for item in report_card(self.enrollment, self.exam_types)
            if item.subject.pk == self.subject.pk
        )
        return super().get_context_data(
            enrollment=self.enrollment,
            exam_types=self.exam_types,
            row=row,
            # Only the htmx row answers carry the flash messages; the full page
            # shows them in base.html.
            oob_messages=True,
            **kwargs,
        )


class StudentGradesEditView(StudentGradesRowView):
    """htmx endpoint: one subject's row of the student grades page as score
    inputs; POST saves them and answers with the read-only row."""

    template_name = "student_grades/partials/student_grades_row_form.html"

    def get_form(self, data=None):
        return StudentSubjectGradesForm(
            data,
            enrollment=self.enrollment,
            subject=self.subject,
            exam_types=self.exam_types,
            recovery_types=ExamType.objects.filter(kind=ExamKind.RECOVERY),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context.setdefault("form", self.get_form())
        *bimester_fields, recovery_fields = form.period_fields()
        context.update(
            bimester_cells=list(
                zip(bimester_fields, context["row"].bimesters, strict=True)
            ),
            recovery_fields=recovery_fields,
        )
        return context

    def post(self, request, *args, **kwargs):
        form = self.get_form(request.POST)
        if not form.is_valid():
            messages.error(
                request, "Corrija as notas destacadas. Nenhuma nota foi salva."
            )
            return self.render_to_response(self.get_context_data(form=form))
        form.save()
        messages.success(request, "Registro atualizado com sucesso")
        # Back to the read-only row, with the grades just saved.
        return TemplateResponse(
            request,
            StudentGradesRowView.template_name,
            StudentGradesRowView.get_context_data(self),
        )


class GradeEntryOptionsView(TemplateView):
    """htmx endpoint: class, subject and bimester selects for the chosen year and class."""

    template_name = "grade_entry/partials/grade_selects.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **grade_selection(self.request), clear_results=True, **kwargs
        )

    def render_to_response(self, context, **kwargs):
        response = super().render_to_response(context, **kwargs)
        # Keep the chosen year and class in the address bar so a reload restores them.
        params = [
            f"{name}={context[key]}"
            for name, key in (
                ("school_year", "selected_year_id"),
                ("school_class", "selected_class_id"),
            )
            if context[key]
        ]
        url = reverse("grades:grade_entry")
        if params:
            url += "?" + "&".join(params)
        response["HX-Push-Url"] = url
        return response


# REPORT CARD VIEWS


class ReportCardView(DetailView):
    model = Enrollment
    template_name = "report_cards/report_card.html"
    context_object_name = "enrollment"
    queryset = Enrollment.objects.select_related(
        "student", "school_class__year", "school_class__program", "enrollment_type"
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["rows"] = report_card(self.object)
        context["bimesters"] = Bimester.choices
        return context
