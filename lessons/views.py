from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import DeleteView, ListView, TemplateView, UpdateView

from accounts.views import ProtectedDeleteMixin, SuccessMessageMixin
from base.search import HtmxFilterMixin, is_htmx_partial
from lessons.forms import (
    LectureDayForm,
    LectureDaySelectForm,
    LectureFilterForm,
    LectureForm,
    TimetableForm,
    TimetableSelectForm,
    series_classes,
)
from lessons.models import Lecture, Weekday
from lessons.services import timetable_grid, weekly_load


class HtmxPartialMixin:
    """TemplateView mixin: only the partial on htmx requests."""

    partial_template_name = None

    def get_template_names(self):
        if is_htmx_partial(self.request):
            return [self.partial_template_name]
        return [self.template_name]


def timetable_url(school_class):
    return f"{reverse('lessons:timetable')}?school_class={school_class.pk}"


# TIMETABLE VIEWS


class TimetableView(HtmxPartialMixin, TemplateView):
    """The weekly timetable of the class picked in ?school_class=<pk>."""

    template_name = "timetable/timetable.html"
    partial_template_name = "timetable/partials/timetable_grid.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        select_form = TimetableSelectForm(self.request.GET or None)
        school_class = (
            select_form.cleaned_data["school_class"] if select_form.is_valid() else None
        )
        context["select_form"] = select_form
        context["school_class"] = school_class
        context["weekdays"] = Weekday.labels
        if school_class:
            context["grid"] = timetable_grid(school_class)
            context["weekly_load"] = weekly_load(school_class)
        return context


class TimetableUpdateView(TemplateView):
    template_name = "timetable/timetable_edit.html"

    def dispatch(self, request, *args, **kwargs):
        self.school_class = get_object_or_404(series_classes(), pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["school_class"] = self.school_class
        context["weekdays"] = Weekday.labels
        context.setdefault("form", TimetableForm(school_class=self.school_class))
        return context

    def post(self, request, *args, **kwargs):
        form = TimetableForm(request.POST, school_class=self.school_class)
        if form.is_valid():
            form.save()
            messages.success(request, "Registro atualizado com sucesso")
            return redirect(timetable_url(self.school_class))
        messages.error(request, "Corrija os horários destacados. Nada foi salvo.")
        return self.render_to_response(self.get_context_data(form=form))


# LECTURE VIEWS


class LectureListView(HtmxFilterMixin, ListView):
    model = Lecture
    template_name = "lectures/lecture_list.html"
    partial_template_name = "lectures/partials/lecture_table.html"
    context_object_name = "lectures"
    paginate_by = 10
    ordering = ("-date", "school_class__name", "period")
    search_fields = ("topic",)
    filter_form_class = LectureFilterForm
    filter_lookups = {
        "school_year": "school_class__year",
        "subject": "subject__subject",
        "date_from": "date__gte",
        "date_to": "date__lte",
    }

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("school_class__year", "subject__subject", "teacher")
        )


class LectureDayView(HtmxPartialMixin, TemplateView):
    """The day sheet of the class and date picked in the query string."""

    template_name = "lectures/lecture_day.html"
    partial_template_name = "lectures/partials/lecture_day_sheet.html"

    def get_sheet_form(self, data=None):
        select_form = LectureDaySelectForm(self.request.GET or None)
        if not (select_form.is_valid() and all(select_form.cleaned_data.values())):
            return select_form, None
        return select_form, LectureDayForm(
            data,
            school_class=select_form.cleaned_data["school_class"],
            date=select_form.cleaned_data["date"],
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
        messages.error(request, "Corrija as aulas destacadas. Nenhuma aula foi salva.")
        return self.render_to_response(self.get_context_data(form=form))


class LectureUpdateView(SuccessMessageMixin, UpdateView):
    model = Lecture
    form_class = LectureForm
    template_name = "lectures/lecture_edit.html"
    success_url = reverse_lazy("lessons:lecture_list")
    success_message = "Registro atualizado com sucesso"


class LectureDeleteView(ProtectedDeleteMixin, DeleteView):
    model = Lecture
    template_name = "lectures/lecture_delete.html"
    success_url = reverse_lazy("lessons:lecture_list")
