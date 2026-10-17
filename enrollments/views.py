from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.models import Account
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

# SCHOOL YEAR VIEWS


class SchoolYearListView(ListView):
    model = SchoolYear
    template_name = "school_years/school_year_list.html"
    context_object_name = "school_years"
    paginate_by = 10


class SchoolYearCreateView(CreateView):
    model = SchoolYear
    template_name = "school_years/school_year_add.html"
    form_class = SchoolYearForm
    success_url = reverse_lazy("school_years:school_year_list")


class SchoolYearUpdateView(UpdateView):
    model = SchoolYear
    template_name = "school_years/school_year_edit.html"
    form_class = SchoolYearForm
    success_url = reverse_lazy("school_years:school_year_list")


class SchoolYearDeleteView(DeleteView):
    model = SchoolYear
    template_name = "school_years/school_year_delete.html"
    success_url = reverse_lazy("school_years:school_year_list")


# NEEDED DOCUMENTS TYPE VIEWS


class NeededDocumentTypeListView(ListView):
    model = NeededDocumentType
    template_name = "needed_documents/needed_document_list.html"
    context_object_name = "needed_documents"
    paginate_by = 10


class NeededDocumentTypeCreateView(CreateView):
    model = NeededDocumentType
    template_name = "needed_documents/needed_document_add.html"
    form_class = NeededDocumentTypeForm
    success_url = reverse_lazy("needed_documents:needed_document_list")


class NeededDocumentTypeUpdateView(UpdateView):
    model = NeededDocumentType
    template_name = "needed_documents/needed_document_edit.html"
    form_class = NeededDocumentTypeForm
    success_url = reverse_lazy("needed_documents:needed_document_list")


class NeededDocumentTypeDeleteView(DeleteView):
    model = NeededDocumentType
    template_name = "needed_documents/needed_document_delete.html"
    success_url = reverse_lazy("needed_documents:needed_document_list")


# ENROLLMENT TYPE VIEWS


class EnrollmentTypeListView(ListView):
    model = EnrollmentType
    template_name = "enrollment_types/enrollment_type_list.html"
    context_object_name = "enrollment_types"
    paginate_by = 10


class EnrollmentTypeCreateView(CreateView):
    model = EnrollmentType
    template_name = "enrollment_types/enrollment_type_add.html"
    form_class = EnrollmentTypeForm
    success_url = reverse_lazy("enrollment_types:enrollment_type_list")


class EnrollmentTypeUpdateView(UpdateView):
    model = EnrollmentType
    template_name = "enrollment_types/enrollment_type_edit.html"
    form_class = EnrollmentTypeForm
    success_url = reverse_lazy("enrollment_types:enrollment_type_list")


class EnrollmentTypeDeleteView(DeleteView):
    model = EnrollmentType
    template_name = "enrollment_types/enrollment_type_delete.html"
    success_url = reverse_lazy("enrollment_types:enrollment_type_list")


# DISCOUNT TYPE VIEWS


class DiscountTypeListView(ListView):
    model = DiscountType
    template_name = "discount_types/discount_type_list.html"
    context_object_name = "discount_types"
    paginate_by = 10


class DiscountTypeCreateView(CreateView):
    model = DiscountType
    template_name = "discount_types/discount_type_add.html"
    form_class = DiscountTypeForm
    success_url = reverse_lazy("discount_types:discount_type_list")


class DiscountTypeUpdateView(UpdateView):
    model = DiscountType
    template_name = "discount_types/discount_type_edit.html"
    form_class = DiscountTypeForm
    success_url = reverse_lazy("discount_types:discount_type_list")


class DiscountTypeDeleteView(DeleteView):
    model = DiscountType
    template_name = "discount_types/discount_type_delete.html"
    success_url = reverse_lazy("discount_types:discount_type_list")


# ENROLLMENT VIEWS


class EnrollmentListView(ListView):
    model = Enrollment
    template_name = "enrollments/enrollment_list.html"
    context_object_name = "enrollments"
    paginate_by = 10


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
        # Synced on GET only, so the POSTed formset matches the rows the user saw.
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
