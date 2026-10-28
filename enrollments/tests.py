from datetime import date
from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from base.testing import LoggedInTestCase
from classes.models import Class
from enrollments.forms import EnrollmentCreateForm, EnrollmentForm
from enrollments.models import (
    DiscountType,
    Enrollment,
    EnrollmentDiscount,
    EnrollmentType,
    NeededDocumentType,
    SchoolYear,
)
from programs.models import Program
from students.models import Guardian, GuardianAssociation, Relationship, Student


class EnrollmentAccountTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school_year = SchoolYear.objects.create(
            begins=date(2027, 1, 10),
            ends=date(2027, 12, 15),
            bi_1_begins=date(2027, 2, 1),
            bi_1_ends=date(2027, 4, 17),
            bi_2_begins=date(2027, 4, 27),
            bi_2_ends=date(2027, 7, 3),
            bi_3_begins=date(2027, 7, 27),
            bi_3_ends=date(2027, 9, 30),
            bi_4_begins=date(2027, 10, 13),
            bi_4_ends=date(2027, 12, 15),
        )
        cls.enrollment_type = EnrollmentType.objects.create(
            program=Program.objects.create(name="Pré ENEM"),
            school_year=cls.school_year,
            total_price=Decimal("1000.00"),
            description="Contrato anual",
        )
        cls.student = Student.objects.create(
            name="Ana Souza", cpf="12345678901", rg="1234567", issuing_authority="SSP"
        )

    def enroll(self, enrolled_at):
        return Enrollment.objects.create(
            student=self.student,
            enrollment_type=self.enrollment_type,
            enrolled_at=enrolled_at,
            due_day=10,
        )

    def test_enrolling_ahead_uses_school_year_for_due_dates(self):
        account = self.enroll(date(2026, 11, 5)).account
        installments = list(account.installments.order_by("number"))
        self.assertEqual(len(installments), 12)
        # Jan 10, 2027 is a Sunday -> Monday 11; Apr 10 is a Saturday -> Monday 12.
        self.assertEqual(installments[0].due_date, date(2027, 1, 11))
        self.assertEqual(installments[1].due_date, date(2027, 2, 10))
        self.assertEqual(installments[3].due_date, date(2027, 4, 12))
        self.assertEqual(installments[-1].due_date, date(2027, 12, 10))

    def test_enrolling_during_school_year_runs_through_december(self):
        account = self.enroll(date(2027, 9, 15)).account
        due_dates = list(
            account.installments.order_by("number").values_list("due_date", flat=True)
        )
        self.assertEqual(
            due_dates,
            [
                date(2027, 9, 15),
                date(2027, 10, 11),  # Oct 10 is a Sunday
                date(2027, 11, 10),
                date(2027, 12, 10),
            ],
        )

    def test_installments_add_up_to_net_value(self):
        # 1000 / 12 doesn't divide evenly: the cents go to the first installment.
        account = self.enroll(date(2026, 11, 5)).account
        amounts = list(
            account.installments.order_by("number").values_list("amount", flat=True)
        )
        self.assertEqual(sum(amounts), account.net_value)
        self.assertEqual(amounts[0], Decimal("83.37"))
        self.assertEqual(set(amounts[1:]), {Decimal("83.33")})


class EnrollmentSettingsRedirectTests(LoggedInTestCase):
    def test_create_views_redirect_to_their_lists(self):
        cases = [
            ("discount_type", {"description": "Irmãos", "percentage": "10"}),
            ("needed_document", {"description": "RG DO ALUNO"}),
        ]
        for name, data in cases:
            with self.subTest(name):
                response = self.client.post(reverse(f"enrollments:{name}_add"), data)
                self.assertRedirects(response, reverse(f"enrollments:{name}_list"))
        self.assertTrue(DiscountType.objects.exists())
        self.assertTrue(NeededDocumentType.objects.exists())


class SchoolClassOptionsTests(LoggedInTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school_year = SchoolYear.objects.create(
            begins=date(2027, 1, 10),
            ends=date(2027, 12, 15),
            bi_1_begins=date(2027, 2, 1),
            bi_1_ends=date(2027, 4, 17),
            bi_2_begins=date(2027, 4, 27),
            bi_2_ends=date(2027, 7, 3),
            bi_3_begins=date(2027, 7, 27),
            bi_3_ends=date(2027, 9, 30),
            bi_4_begins=date(2027, 10, 13),
            bi_4_ends=date(2027, 12, 15),
        )
        program = Program.objects.create(name="Ensino Médio")
        other_program = Program.objects.create(name="Pré ENEM")
        cls.enrollment_type = EnrollmentType.objects.create(
            program=program,
            level="2",
            school_year=cls.school_year,
            total_price=Decimal("1000.00"),
            description="2ª série",
        )
        cls.matching = Class.objects.create(
            program=program, year=cls.school_year, grade_level=2, name="A"
        )
        cls.other_grade = Class.objects.create(
            program=program, year=cls.school_year, grade_level=1, name="B"
        )
        cls.other_program = Class.objects.create(
            program=other_program, year=cls.school_year, grade_level=2, name="C"
        )

    def test_options_are_filtered_by_enrollment_type_grade(self):
        response = self.client.get(
            reverse("enrollments:school_class_options"),
            {"enrollment_type": self.enrollment_type.pk},
            HTTP_HX_REQUEST="true",
        )
        self.assertTemplateUsed(
            response, "enrollments/partials/school_class_field.html"
        )
        self.assertEqual(
            list(response.context["form"].fields["school_class"].queryset),
            [self.matching],
        )

    def test_option_label_shows_active_students_and_capacity(self):
        self.matching.capacity = 50
        self.matching.save()
        response = self.client.get(
            reverse("enrollments:school_class_options"),
            {"enrollment_type": self.enrollment_type.pk},
        )
        self.assertContains(response, f"{self.matching} (0/50)")

    def test_no_options_without_enrollment_type(self):
        response = self.client.get(reverse("enrollments:school_class_options"))
        self.assertFalse(response.context["form"].fields["school_class"].queryset)

    def test_bound_form_rejects_class_of_another_grade(self):
        form = EnrollmentForm(
            data={
                "enrollment_type": self.enrollment_type.pk,
                "school_class": self.other_grade.pk,
            }
        )
        self.assertIn("school_class", form.errors)


class EnrollmentDiscountTests(LoggedInTestCase):
    @classmethod
    def setUpTestData(cls):
        school_year = SchoolYear.objects.create(
            begins=date(2027, 1, 10), ends=date(2027, 12, 15)
        )
        cls.enrollment_type = EnrollmentType.objects.create(
            program=Program.objects.create(name="Pré ENEM"),
            school_year=school_year,
            total_price=Decimal("1000.00"),
        )
        cls.student = Student.objects.create(
            name="Ana Souza", cpf="12345678901", rg="1234567", issuing_authority="SSP"
        )
        GuardianAssociation.objects.create(
            student=cls.student,
            guardian=Guardian.objects.create(
                name="Maria Souza", cpf="00275010198", rg="7654321"
            ),
            relationship=Relationship.MOTHER,
            is_financial=True,
        )
        cls.siblings = DiscountType.objects.create(
            description="IRMÃOS", percentage=Decimal(10)
        )
        cls.former = DiscountType.objects.create(
            description="ALUNO ANTIGO", percentage=Decimal(20)
        )

    def form(self, **data):
        return EnrollmentCreateForm(
            data={
                "student": self.student.pk,
                "enrollment_type": self.enrollment_type.pk,
                "status": "A",
                "due_day": 10,
                **data,
            }
        )

    def test_discounts_are_summed_into_the_account(self):
        form = self.form(
            discount_types=[self.siblings.pk, self.former.pk],
            custom_discount_percent="5",
            custom_discount_observation="Desconto autorizado pela direção",
        )
        self.assertTrue(form.is_valid(), form.errors)
        enrollment = form.save()

        self.assertEqual(enrollment.discount_percent, Decimal(35))
        self.assertEqual(enrollment.account.discount_value, Decimal("350.00"))
        self.assertEqual(enrollment.account.net_value, Decimal("650.00"))
        custom = enrollment.discounts.get(discount_type=None)
        self.assertEqual(custom.percentage, Decimal(5))
        self.assertEqual(custom.observation, "Desconto autorizado pela direção")
        self.assertEqual(enrollment.discounts.count(), 3)

    def test_type_percentage_is_copied(self):
        form = self.form(discount_types=[self.siblings.pk])
        self.assertTrue(form.is_valid(), form.errors)
        enrollment = form.save()
        DiscountType.objects.filter(pk=self.siblings.pk).update(percentage=50)

        self.assertEqual(enrollment.discounts.get().percentage, Decimal(10))

    def test_no_discount(self):
        form = self.form()
        self.assertTrue(form.is_valid(), form.errors)
        enrollment = form.save()

        self.assertEqual(enrollment.discount_percent, Decimal(0))
        self.assertFalse(enrollment.discounts.exists())

    def test_custom_discount_requires_observation(self):
        form = self.form(custom_discount_percent="15")
        self.assertFalse(form.is_valid())
        self.assertIn("custom_discount_observation", form.errors)

    def test_observation_requires_custom_percentage(self):
        form = self.form(custom_discount_observation="Autorizado pela direção")
        self.assertFalse(form.is_valid())
        self.assertIn("custom_discount_percent", form.errors)

    def test_discounts_cannot_exceed_100_percent(self):
        form = self.form(
            discount_types=[self.siblings.pk, self.former.pk],
            custom_discount_percent="80",
            custom_discount_observation="Bolsa integral",
        )
        self.assertFalse(form.is_valid())
        self.assertIn("discount_types", form.errors)
        self.assertFalse(Enrollment.objects.exists())

    def test_create_view_saves_discounts(self):
        response = self.client.post(
            reverse("enrollments:enrollment_add"),
            {
                "student": self.student.pk,
                "enrollment_type": self.enrollment_type.pk,
                "status": "A",
                "due_day": 10,
                "discount_types": [self.former.pk],
            },
        )
        enrollment = Enrollment.objects.get()
        self.assertRedirects(
            response, reverse("enrollments:enrollment_edit", args=[enrollment.pk])
        )
        self.assertEqual(enrollment.discount_percent, Decimal(20))

        response = self.client.get(
            reverse("enrollments:enrollment_edit", args=[enrollment.pk])
        )
        self.assertContains(response, "ALUNO ANTIGO")

    def test_database_requires_observation_on_custom_discount(self):
        enrollment = Enrollment.objects.create(
            student=self.student, enrollment_type=self.enrollment_type, due_day=10
        )
        with self.assertRaises(IntegrityError):
            EnrollmentDiscount.objects.create(
                enrollment=enrollment, percentage=Decimal(5)
            )
