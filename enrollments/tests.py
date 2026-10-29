from datetime import date
from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from base.testing import LoggedInTestCase
from classes.models import Class
from enrollments.forms import EnrollmentCreateForm, EnrollmentForm, SchoolYearForm
from enrollments.models import (
    DiscountGroup,
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

    def amounts(self, account):
        return list(
            account.installments.order_by("number").values_list("amount", flat=True)
        )

    def test_first_installment_is_one_twelfth(self):
        # 1000 / 12 = 83.33; the other 916.67 split over 11 months doesn't
        # divide evenly: the cents go to the second installment.
        account = self.enroll(date(2026, 11, 5)).account
        amounts = self.amounts(account)
        self.assertEqual(sum(amounts), account.net_value)
        self.assertEqual(amounts[0], Decimal("83.33"))
        self.assertEqual(amounts[1], Decimal("83.37"))
        self.assertEqual(set(amounts[2:]), {Decimal("83.33")})

    def test_remaining_eleven_twelfths_split_over_remaining_months(self):
        account = self.enroll(date(2027, 9, 15)).account
        self.assertEqual(
            self.amounts(account),
            [
                Decimal("83.33"),
                Decimal("305.57"),
                Decimal("305.55"),
                Decimal("305.55"),
            ],
        )

    def test_single_installment_carries_the_whole_contract(self):
        account = self.enroll(date(2027, 12, 1)).account
        self.assertEqual(self.amounts(account), [Decimal("1000.00")])


class SchoolYearFormTests(TestCase):
    def setUp(self):
        self.data = {"begins": "2027-01-10", "ends": "2027-12-15"}

    def test_requires_school_days_and_total_hours(self):
        form = SchoolYearForm(data=self.data)
        self.assertFalse(form.is_valid())
        self.assertIn("school_days", form.errors)
        self.assertIn("total_hours", form.errors)

    def test_saves_school_days_and_total_hours(self):
        form = SchoolYearForm(
            data={**self.data, "school_days": "200", "total_hours": "1000"}
        )
        self.assertTrue(form.is_valid(), form.errors)
        school_year = form.save()
        self.assertEqual(school_year.school_days, 200)
        self.assertEqual(school_year.total_hours, 1000)

    def test_rejects_zero(self):
        form = SchoolYearForm(
            data={**self.data, "school_days": "0", "total_hours": "0"}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("school_days", form.errors)
        self.assertIn("total_hours", form.errors)


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


class EnrollmentContractTests(LoggedInTestCase):
    @classmethod
    def setUpTestData(cls):
        school_year = SchoolYear.objects.create(
            begins=date(2027, 1, 10), ends=date(2027, 12, 15)
        )
        student = Student.objects.create(
            name="Ana Souza", cpf="12345678901", rg="1234567", issuing_authority="SSP"
        )
        GuardianAssociation.objects.create(
            student=student,
            guardian=Guardian.objects.create(
                name="Maria Souza", cpf="00275010198", rg="7654321"
            ),
            relationship=Relationship.MOTHER,
            is_financial=True,
        )
        # Mid-year and without a class: 4 installments, not 12.
        cls.enrollment = Enrollment.objects.create(
            student=student,
            enrollment_type=EnrollmentType.objects.create(
                program=Program.objects.create(name="Pré ENEM"),
                school_year=school_year,
                level="2",
                total_price=Decimal("14999.00"),
            ),
            enrolled_at=date(2027, 9, 15),
            due_day=10,
        )

    def test_contract_lists_the_billed_installments(self):
        response = self.client.get(
            reverse("enrollments:enrollment_preview", args=[self.enrollment.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2ª Série - 2027")
        self.assertEqual(len(response.context["installments"]), 4)
        self.assertContains(response, "<td>4/4</td>", html=True)
        self.assertContains(response, "10/12/2027")
        self.assertContains(response, "R$ 1.249,92")
        self.assertContains(response, "R$ 4.583,04")
        self.assertContains(response, "R$ 4.583,02", count=2)


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

    def test_each_group_has_its_own_discounts(self):
        form = self.form(
            first_discount_types=[self.siblings.pk, self.former.pk],
            first_custom_discount_percent="5",
            first_custom_discount_observation="Desconto autorizado pela direção",
            remaining_discount_types=[self.siblings.pk],
        )
        self.assertTrue(form.is_valid(), form.errors)
        enrollment = form.save()

        self.assertEqual(enrollment.first_discount_percent, Decimal(35))
        self.assertEqual(enrollment.remaining_discount_percent, Decimal(10))
        # 35% of 83.33 + 10% of 916.67
        self.assertEqual(enrollment.account.discount_value, Decimal("120.84"))
        self.assertEqual(enrollment.account.net_value, Decimal("879.16"))
        amounts = list(
            enrollment.account.installments.order_by("number").values_list(
                "amount", flat=True
            )
        )
        self.assertEqual(amounts[0], Decimal("54.16"))
        self.assertEqual(set(amounts[1:]), {Decimal("75.00")})

        custom = enrollment.discounts.get(discount_type=None)
        self.assertEqual(custom.group, DiscountGroup.FIRST)
        self.assertEqual(custom.observation, "Desconto autorizado pela direção")
        self.assertEqual(enrollment.discounts.filter(group="F").count(), 3)
        self.assertEqual(enrollment.discounts.filter(group="R").count(), 1)

    def test_discount_only_on_remaining_installments(self):
        form = self.form(remaining_discount_types=[self.former.pk])
        self.assertTrue(form.is_valid(), form.errors)
        enrollment = form.save()

        self.assertEqual(enrollment.first_discount_percent, Decimal(0))
        first = enrollment.account.installments.get(number=1)
        self.assertEqual(first.amount, Decimal("83.33"))
        # 20% of 916.67
        self.assertEqual(enrollment.account.discount_value, Decimal("183.33"))

    def test_type_percentage_is_copied(self):
        form = self.form(first_discount_types=[self.siblings.pk])
        self.assertTrue(form.is_valid(), form.errors)
        enrollment = form.save()
        DiscountType.objects.filter(pk=self.siblings.pk).update(percentage=50)

        self.assertEqual(enrollment.discounts.get().percentage, Decimal(10))

    def test_no_discount(self):
        form = self.form()
        self.assertTrue(form.is_valid(), form.errors)
        enrollment = form.save()

        self.assertEqual(enrollment.first_discount_percent, Decimal(0))
        self.assertEqual(enrollment.remaining_discount_percent, Decimal(0))
        self.assertFalse(enrollment.discounts.exists())
        self.assertEqual(enrollment.account.net_value, Decimal("1000.00"))

    def test_custom_discount_requires_observation(self):
        form = self.form(remaining_custom_discount_percent="15")
        self.assertFalse(form.is_valid())
        self.assertIn("remaining_custom_discount_observation", form.errors)

    def test_observation_requires_custom_percentage(self):
        form = self.form(first_custom_discount_observation="Autorizado pela direção")
        self.assertFalse(form.is_valid())
        self.assertIn("first_custom_discount_percent", form.errors)

    def test_each_group_cannot_exceed_100_percent(self):
        form = self.form(
            first_discount_types=[self.siblings.pk, self.former.pk],
            remaining_discount_types=[self.siblings.pk, self.former.pk],
            remaining_custom_discount_percent="80",
            remaining_custom_discount_observation="Bolsa integral",
        )
        self.assertFalse(form.is_valid())
        self.assertNotIn("first_discount_types", form.errors)
        self.assertIn("remaining_discount_types", form.errors)
        self.assertFalse(Enrollment.objects.exists())

    def test_create_view_saves_discounts(self):
        response = self.client.post(
            reverse("enrollments:enrollment_add"),
            {
                "student": self.student.pk,
                "enrollment_type": self.enrollment_type.pk,
                "status": "A",
                "due_day": 10,
                "first_discount_types": [self.former.pk],
                "remaining_discount_types": [self.former.pk],
            },
        )
        enrollment = Enrollment.objects.get()
        self.assertRedirects(
            response, reverse("enrollments:enrollment_edit", args=[enrollment.pk])
        )
        self.assertEqual(enrollment.first_discount_percent, Decimal(20))
        self.assertEqual(enrollment.remaining_discount_percent, Decimal(20))

        response = self.client.get(
            reverse("enrollments:enrollment_edit", args=[enrollment.pk])
        )
        self.assertContains(response, "ALUNO ANTIGO")
        self.assertContains(response, "Demais parcelas")

    def test_database_requires_observation_on_custom_discount(self):
        enrollment = Enrollment.objects.create(
            student=self.student, enrollment_type=self.enrollment_type, due_day=10
        )
        with self.assertRaises(IntegrityError):
            EnrollmentDiscount.objects.create(
                enrollment=enrollment, group=DiscountGroup.FIRST, percentage=Decimal(5)
            )

    def test_edit_form_locks_student_and_enrollment_type(self):
        enrollment = Enrollment.objects.create(
            student=self.student, enrollment_type=self.enrollment_type, due_day=10
        )
        other_student = Student.objects.create(
            name="Bruno Lima", cpf="98765432100", rg="7777777", issuing_authority="SSP"
        )
        other_type = EnrollmentType.objects.create(
            program=self.enrollment_type.program,
            school_year=self.enrollment_type.school_year,
            total_price=Decimal("500.00"),
        )
        form = EnrollmentForm(
            instance=enrollment,
            data={
                "student": other_student.pk,
                "enrollment_type": other_type.pk,
                "status": "A",
                "due_day": 15,
            },
        )
        self.assertTrue(form.fields["student"].disabled)
        self.assertTrue(form.fields["enrollment_type"].disabled)
        self.assertTrue(form.is_valid(), form.errors)
        enrollment = form.save()

        self.assertEqual(enrollment.student, self.student)
        self.assertEqual(enrollment.enrollment_type, self.enrollment_type)
        self.assertEqual(enrollment.due_day, 15)

    def test_create_form_leaves_student_and_enrollment_type_editable(self):
        form = self.form()
        self.assertFalse(form.fields["student"].disabled)
        self.assertFalse(form.fields["enrollment_type"].disabled)
