from pathlib import Path

from django.contrib.staticfiles import finders
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy
from django.utils.text import slugify
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)
from weasyprint import HTML

from accounts.models import Account
from base.search import HtmxSearchMixin
from enrollments.forms import (
    DiscountTypeForm,
    EnrollmentForm,
    EnrollmentNeededDocumentFormSet,
    EnrollmentTypeForm,
    InstallmentFormSet,
    NeededDocumentTypeForm,
    SchoolYearForm,
)
from enrollments.models import (
    DiscountType,
    Enrollment,
    EnrollmentNeededDocument,
    EnrollmentType,
    NeededDocumentType,
    SchoolYear,
)
from students.models import Guardian
from utils.format.number_values import format_cpf, format_zip_code

# SCHOOL YEAR VIEWS


class SchoolYearListView(HtmxSearchMixin, ListView):
    model = SchoolYear
    template_name = "school_years/school_year_list.html"
    context_object_name = "school_years"
    partial_template_name = "school_years/partials/school_year_table.html"
    paginate_by = 10
    ordering = ("-begins",)
    search_fields = ("begins", "ends")


class SchoolYearCreateView(CreateView):
    model = SchoolYear
    template_name = "school_years/school_year_add.html"
    form_class = SchoolYearForm
    success_url = reverse_lazy("enrollments:school_year_list")


class SchoolYearUpdateView(UpdateView):
    model = SchoolYear
    template_name = "school_years/school_year_edit.html"
    form_class = SchoolYearForm
    success_url = reverse_lazy("enrollments:school_year_list")


class SchoolYearDeleteView(DeleteView):
    model = SchoolYear
    template_name = "school_years/school_year_delete.html"
    success_url = reverse_lazy("enrollments:school_year_list")


# NEEDED DOCUMENTS TYPE VIEWS


class NeededDocumentTypeListView(HtmxSearchMixin, ListView):
    model = NeededDocumentType
    template_name = "needed_documents/needed_document_list.html"
    context_object_name = "needed_documents"
    partial_template_name = "needed_documents/partials/needed_document_table.html"
    paginate_by = 10
    ordering = ("description",)
    search_fields = ("description",)


class NeededDocumentTypeCreateView(CreateView):
    model = NeededDocumentType
    template_name = "needed_documents/needed_document_add.html"
    form_class = NeededDocumentTypeForm
    success_url = reverse_lazy("enrollments:needed_document_list")


class NeededDocumentTypeUpdateView(UpdateView):
    model = NeededDocumentType
    template_name = "needed_documents/needed_document_edit.html"
    form_class = NeededDocumentTypeForm
    success_url = reverse_lazy("enrollments:needed_document_list")


class NeededDocumentTypeDeleteView(DeleteView):
    model = NeededDocumentType
    template_name = "needed_documents/needed_document_delete.html"
    success_url = reverse_lazy("enrollments:needed_document_list")


# ENROLLMENT TYPE VIEWS


class EnrollmentTypeListView(HtmxSearchMixin, ListView):
    model = EnrollmentType
    template_name = "enrollment_types/enrollment_type_list.html"
    context_object_name = "enrollment_types"
    partial_template_name = "enrollment_types/partials/enrollment_type_table.html"
    paginate_by = 10
    ordering = ("-school_year__begins", "program__name", "level")
    search_fields = ("program__name", "description", "school_year__begins")


class EnrollmentTypeCreateView(CreateView):
    model = EnrollmentType
    template_name = "enrollment_types/enrollment_type_add.html"
    form_class = EnrollmentTypeForm
    success_url = reverse_lazy("enrollments:enrollment_type_list")


class EnrollmentTypeUpdateView(UpdateView):
    model = EnrollmentType
    template_name = "enrollment_types/enrollment_type_edit.html"
    form_class = EnrollmentTypeForm
    success_url = reverse_lazy("enrollments:enrollment_type_list")


class EnrollmentTypeDeleteView(DeleteView):
    model = EnrollmentType
    template_name = "enrollment_types/enrollment_type_delete.html"
    success_url = reverse_lazy("enrollments:enrollment_type_list")


# DISCOUNT TYPE VIEWS


class DiscountTypeListView(HtmxSearchMixin, ListView):
    model = DiscountType
    template_name = "discount_types/discount_type_list.html"
    context_object_name = "discount_types"
    partial_template_name = "discount_types/partials/discount_type_table.html"
    paginate_by = 10
    ordering = ("description",)
    search_fields = ("description",)


class DiscountTypeCreateView(CreateView):
    model = DiscountType
    template_name = "discount_types/discount_type_add.html"
    form_class = DiscountTypeForm
    success_url = reverse_lazy("enrollments:discount_type_list")


class DiscountTypeUpdateView(UpdateView):
    model = DiscountType
    template_name = "discount_types/discount_type_edit.html"
    form_class = DiscountTypeForm
    success_url = reverse_lazy("enrollments:discount_type_list")


class DiscountTypeDeleteView(DeleteView):
    model = DiscountType
    template_name = "discount_types/discount_type_delete.html"
    success_url = reverse_lazy("enrollments:discount_type_list")


# ENROLLMENT VIEWS


class EnrollmentListView(HtmxSearchMixin, ListView):
    model = Enrollment
    queryset = Enrollment.objects.select_related(
        "student",
        "enrollment_type__program",
        "enrollment_type__school_year",
        "school_class__year",
    )
    template_name = "enrollments/enrollment_list.html"
    context_object_name = "enrollments"
    partial_template_name = "enrollments/partials/enrollment_table.html"
    paginate_by = 10
    ordering = ("-enrolled_at", "student__name")
    search_fields = (
        "student__name",
        "student__social_name",
        "student__registration",
        "school_class__name",
        "enrollment_type__program__name",
    )


class EnrollmentCreateView(CreateView):
    model = Enrollment
    template_name = "enrollments/enrollment_add.html"
    form_class = EnrollmentForm

    def get_success_url(self):
        return reverse("enrollments:enrollment_edit", kwargs={"pk": self.object.pk})


class EnrollmentUpdateView(UpdateView):
    model = Enrollment
    template_name = "enrollments/enrollment_edit.html"
    form_class = EnrollmentForm
    success_url = reverse_lazy("enrollments:enrollment_list")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.sync_documents()
        return self.render_to_response(self.get_context_data())

    def get_account(self):
        try:
            return self.object.account
        except Account.DoesNotExist:
            return None

    def get_formsets(self, data=None):
        account = self.get_account()
        return {
            "documents_formset": EnrollmentNeededDocumentFormSet(
                data,
                instance=self.object,
                prefix="documents",
                queryset=EnrollmentNeededDocument.objects.select_related("type"),
            ),
            "installment_formset": (
                InstallmentFormSet(data, instance=account, prefix="installments")
                if account
                else None
            ),
        }

    def get_context_data(self, **kwargs):
        if "documents_formset" not in kwargs:
            kwargs.update(self.get_formsets())
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        formsets = self.get_formsets(request.POST)
        active = [fs for fs in formsets.values() if fs is not None]
        if form.is_valid() and all(fs.is_valid() for fs in active):
            with transaction.atomic():
                self.object = form.save()
                for fs in active:
                    fs.save()
            return redirect(self.get_success_url())
        return self.render_to_response(self.get_context_data(form=form, **formsets))


class SchoolClassOptionsView(TemplateView):
    """htmx endpoint: the school class field filtered by ?enrollment_type=<pk>."""

    template_name = "enrollments/partials/school_class_field.html"

    def get_context_data(self, **kwargs):
        form = EnrollmentForm(
            initial={"enrollment_type": self.request.GET.get("enrollment_type")}
        )
        return super().get_context_data(form=form, **kwargs)


# PRINT REPORT


def build_report_context(pk):

    enrollment = get_object_or_404(Enrollment, pk=pk)
    student_name = enrollment.student.name
    school_year = enrollment.enrollment_type.school_year.begins.year
    grade = enrollment.school_class.grade_level
    student_cpf = enrollment.student.cpf
    student_zip_code = format_zip_code(enrollment.student.zip_code)
    student_mobile = enrollment.student.mobile
    student_address = f"{enrollment.student.address}, {enrollment.student.neighborhood}, {enrollment.student.city} - {enrollment.student.state}"
    financial_guardian = Guardian.objects.filter(
        student_links__student=enrollment.student,
        student_links__is_financial=True,
    ).first()
    financial_guardian_name = financial_guardian.name
    financial_guardian_cpf = financial_guardian.cpf
    financial_guardian_address = f"{financial_guardian.address}, {financial_guardian.neighborhood}, {financial_guardian.city} - {financial_guardian.state}"
    financial_guardian_mobile = financial_guardian.mobile
    financial_guardian_email = financial_guardian.email
    program = enrollment.enrollment_type
    total_price = enrollment.gross_value
    discount_percentage = enrollment.discount_percent
    has_discount = bool(discount_percentage)
    discount_amount = enrollment.discount_value

    start_date_of_the_contract = enrollment.enrollment_type.start_date
    end_date_of_the_contract = enrollment.enrollment_type.end_date
    ultima_parcela = f"{enrollment.due_day}/12/{school_year}"
    context = {
        "student_name": student_name,
        "school_year": school_year,
        "grade": grade,
        "student_cpf": format_cpf(student_cpf),
        "student_zip_code": student_zip_code,
        "student_mobile": student_mobile,
        "student_address": student_address,
        "financial_guardian_name": financial_guardian_name,
        "financial_guardian_cpf": format_cpf(financial_guardian_cpf),
        "financial_guardian_address": financial_guardian_address,
        "financial_guardian_mobile": financial_guardian_mobile,
        "financial_guardian_email": financial_guardian_email,
        "program": program,
        "total_price": total_price,
        "has_discount": has_discount,
        "discount_percentage": discount_percentage,
        "discount_amount": discount_amount,
        "start_date_of_the_contract": start_date_of_the_contract,
        "end_date_of_the_contract": end_date_of_the_contract,
        "numero_de_parcelas": 12,
        "ultima_parcela": ultima_parcela,
    }
    return context


def generate_report_view(request, pk):
    context = build_report_context(pk)
    context["object_id"] = pk
    return TemplateResponse(request, "enrollments/preview_enrollment.html", context)


def generate_report_pdf_view(request, pk):
    context = build_report_context(pk)
    context["pdf"] = True
    context["logo_src"] = Path(finders.find("img/unico_logo_stamp.png")).as_uri()
    html = render_to_string(
        "enrollments/preview_enrollment.html", context, request=request
    )
    pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()

    filename = f"contrato-{slugify(context['student_name'])}.pdf"
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
