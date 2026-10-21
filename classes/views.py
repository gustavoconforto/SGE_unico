from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)

from base.search import HtmxSearchMixin
from classes.forms import ClassForm
from classes.models import Class
from enrollments.models import EnrollmentStatus, SchoolYear
from grades.models import GradeLevelSubject
from students.models import Student


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


def get_int_param(request, name):
    value = request.GET.get(name, "")
    return int(value) if value.isdigit() else None


def classes_of_year(year_id):
    if year_id is None:
        return Class.objects.none()
    return Class.objects.select_related("year").filter(year_id=year_id)


class ClassDetailView(HtmxSearchMixin, ListView):
    """Students actively enrolled in the class picked in ?school_class=<pk>."""

    model = Student
    template_name = "classes_detail/class_detail.html"
    context_object_name = "students"
    partial_template_name = "classes/partials/class_detail_table.html"
    paginate_by = 10
    ordering = ("name",)
    search_fields = ("name",)

    def get_queryset(self):
        class_id = get_int_param(self.request, "school_class")
        if class_id is None:
            return Student.objects.none()
        return (
            super()
            .get_queryset()
            .filter(
                enrollments__school_class_id=class_id,
                enrollments__status=EnrollmentStatus.ACTIVE,
            )
            .distinct()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year_id = get_int_param(self.request, "school_year")
        context["school_years"] = SchoolYear.objects.order_by("-begins")
        context["selected_year_id"] = year_id
        context["classes"] = classes_of_year(year_id)
        class_id = get_int_param(self.request, "school_class")
        context["selected_class_id"] = class_id
        selected_class = Class.objects.filter(pk=class_id).first() if class_id else None
        context["selected_class"] = selected_class
        context["level_subjects"] = (
            GradeLevelSubject.objects.filter(grade_level=selected_class.grade_level)
            .select_related("subject")
            .prefetch_related("teachers")
            if selected_class and selected_class.grade_level
            else GradeLevelSubject.objects.none()
        )
        return context


class ClassOptionsView(TemplateView):
    """htmx endpoint: the class select filtered by ?school_year=<pk>."""

    template_name = "classes/partials/class_select.html"

    def get_context_data(self, **kwargs):
        year_id = get_int_param(self.request, "school_year")
        return super().get_context_data(
            classes=classes_of_year(year_id),
            selected_year_id=year_id,
            clear_results=True,
            **kwargs,
        )

    def render_to_response(self, context, **kwargs):
        response = super().render_to_response(context, **kwargs)
        # Keep the chosen year in the address bar so a reload restores it.
        url = reverse("classes:class_detail")
        if context["selected_year_id"]:
            url += f"?school_year={context['selected_year_id']}"
        response["HX-Push-Url"] = url
        return response
