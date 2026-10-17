from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    UpdateView,
)

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


def school_year_list_view(request):
    school_years = SchoolYear.objects.all()

    context = {"school_years": school_years}
    return render(request, "school_years/school_year_list.html", context)


def school_year_add_view(request):
    if request.method == "POST":
        form = SchoolYearForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("enrollments:school_year_list")

    else:
        form = SchoolYearForm()

    context = {"form": form}
    return render(request, "school_years/school_year_add.html", context)


def school_year_edit_view(request, pk):
    school_year = get_object_or_404(SchoolYear, pk=pk)

    if request.method == "POST":
        form = SchoolYearForm(request.POST, instance=school_year)

        if form.is_valid():
            form.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("enrollments:school_year_list")

    form = SchoolYearForm(instance=school_year)

    context = {"form": form}
    return render(request, "school_years/school_year_edit.html", context)


def school_year_delete_view(request, pk):
    school_year = get_object_or_404(SchoolYear, pk=pk)

    if request.method == "POST":
        school_year.delete()
        messages.warning(request, "Registro deletado com sucesso")
        return redirect("enrollments:school_year_list")

    form = SchoolYearForm(instance=school_year)
    for field in form.fields.values():
        field.disabled = True

    context = {"form": form}
    return render(request, "school_years/school_year_delete.html", context)


# NEEDED DOCUMENTS TYPE VIEWS


def needed_document_list_view(request):
    needed_documents = NeededDocumentType.objects.all()

    context = {"needed_documents": needed_documents}
    return render(request, "needed_documents/needed_document_list.html", context)


def needed_document_add_view(request):
    if request.method == "POST":
        form = NeededDocumentTypeForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("enrollments:needed_document_list")

    else:
        form = NeededDocumentTypeForm()

    context = {"form": form}
    return render(request, "needed_documents/needed_document_add.html", context)


def needed_document_edit_view(request, pk):
    needed_document = get_object_or_404(NeededDocumentType, pk=pk)

    if request.method == "POST":
        form = NeededDocumentTypeForm(request.POST, instance=needed_document)

        if form.is_valid():
            form.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("enrollments:needed_document_list")

    form = NeededDocumentTypeForm(instance=needed_document)

    context = {"form": form}
    return render(request, "needed_documents/needed_document_edit.html", context)


def needed_document_delete_view(request, pk):
    needed_document = get_object_or_404(NeededDocumentType, pk=pk)

    if request.method == "POST":
        needed_document.delete()
        messages.warning(request, "Registro deletado com sucesso")
        return redirect("enrollments:needed_document_list")

    form = NeededDocumentTypeForm(instance=needed_document)
    for field in form.fields.values():
        field.disabled = True

    context = {"form": form}
    return render(request, "needed_documents/needed_document_delete.html", context)


# ENROLLMENT TYPE VIEWS


def enrollment_type_list_view(request):
    enrollment_types = EnrollmentType.objects.all()

    context = {"enrollment_types": enrollment_types}
    return render(request, "enrollment_types/enrollment_type_list.html", context)


def enrollment_type_add_view(request):
    if request.method == "POST":
        form = EnrollmentTypeForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("enrollments:enrollment_type_list")

    else:
        form = EnrollmentTypeForm()
        form.fields["start_date"].disabled = True
        form.fields["end_date"].disabled = True

    context = {"form": form}
    return render(request, "enrollment_types/enrollment_type_add.html", context)


def enrollment_type_edit_view(request, pk):
    enrollment_type = get_object_or_404(EnrollmentType, pk=pk)

    if request.method == "POST":
        form = EnrollmentTypeForm(request.POST, instance=enrollment_type)

        if form.is_valid():
            form.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("enrollments:enrollment_type_list")

    form = EnrollmentTypeForm(instance=enrollment_type)
    form.fields["start_date"].disabled = True
    form.fields["end_date"].disabled = True

    context = {"form": form}
    return render(request, "enrollment_types/enrollment_type_edit.html", context)


def enrollment_type_delete_view(request, pk):
    enrollment_type = get_object_or_404(EnrollmentType, pk=pk)

    if request.method == "POST":
        enrollment_type.delete()
        messages.warning(request, "Registro deletado com sucesso")
        return redirect("enrollments:enrollment_type_list")

    form = EnrollmentTypeForm(instance=enrollment_type)
    for field in form.fields.values():
        field.disabled = True

    context = {"form": form}
    return render(request, "enrollment_types/enrollment_type_delete.html", context)


# DISCOUNT TYPE VIEWS


def discount_type_list_view(request):
    discount_types = DiscountType.objects.all()

    context = {"discount_types": discount_types}
    return render(request, "discount_types/discount_type_list.html", context)


def discount_type_add_view(request):
    if request.method == "POST":
        form = DiscountTypeForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("enrollments:discount_type_list")

    else:
        form = DiscountTypeForm()

    context = {"form": form}
    return render(request, "discount_types/discount_type_add.html", context)


def discount_type_edit_view(request, pk):
    discount_type = get_object_or_404(DiscountType, pk=pk)

    if request.method == "POST":
        form = DiscountTypeForm(request.POST, instance=discount_type)

        if form.is_valid():
            form.save()
            messages.success(request, "Registro cadastrado com sucesso")
            return redirect("enrollments:discount_type_list")

    form = DiscountTypeForm(instance=discount_type)

    context = {"form": form}
    return render(request, "discount_types/discount_type_edit.html", context)


def discount_type_delete_view(request, pk):
    discount_type = get_object_or_404(DiscountType, pk=pk)

    if request.method == "POST":
        discount_type.delete()
        messages.warning(request, "Registro deletado com sucesso")
        return redirect("enrollments:discount_type_list")

    form = DiscountTypeForm(instance=discount_type)
    for field in form.fields.values():
        field.disabled = True

    context = {"form": form}
    return render(request, "discount_types/discount_type_delete.html", context)


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


class EnrollmentDeleteView(DeleteView):
    model = Enrollment
    template_name = "enrollments/enrollment_delete.html"
    success_url = reverse_lazy("enrollments:enrollment_list")
