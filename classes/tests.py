from datetime import date
from decimal import Decimal

from django.urls import reverse

from base.testing import LoggedInTestCase
from classes.models import Class
from enrollments.models import (
    Enrollment,
    EnrollmentStatus,
    EnrollmentType,
    SchoolYear,
)
from programs.models import Program
from students.models import Student


class ClassDetailViewTests(LoggedInTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school_year = school_year = SchoolYear.objects.create(
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
        enrollment_type = EnrollmentType.objects.create(
            program=program,
            school_year=school_year,
            total_price=Decimal("1000.00"),
            description="Contrato anual",
        )
        cls.school_class = Class.objects.create(
            program=program, year=school_year, name="A"
        )
        other_class = Class.objects.create(program=program, year=school_year, name="B")
        other_year = SchoolYear.objects.create(
            begins=date(2028, 1, 10),
            ends=date(2028, 12, 15),
            bi_1_begins=date(2028, 2, 1),
            bi_1_ends=date(2028, 4, 17),
            bi_2_begins=date(2028, 4, 27),
            bi_2_ends=date(2028, 7, 3),
            bi_3_begins=date(2028, 7, 27),
            bi_3_ends=date(2028, 9, 30),
            bi_4_begins=date(2028, 10, 13),
            bi_4_ends=date(2028, 12, 15),
        )
        Class.objects.create(program=program, year=other_year, name="A")
        cls.year_classes = [cls.school_class, other_class]

        def enroll(name, cpf, school_class, status=EnrollmentStatus.ACTIVE):
            student = Student.objects.create(
                name=name, cpf=cpf, rg=cpf[-7:], issuing_authority="SSP"
            )
            Enrollment.objects.create(
                student=student,
                enrollment_type=enrollment_type,
                school_class=school_class,
                status=status,
                enrolled_at=date(2027, 1, 15),
                due_day=10,
            )
            return student

        cls.ana = enroll("Ana Souza", "12345678901", cls.school_class)
        enroll("Bruno Lima", "12345678902", other_class)
        enroll("Carla Dias", "12345678903", cls.school_class, EnrollmentStatus.DROPPED)

    def test_page_without_class_lists_no_students(self):
        response = self.client.get(reverse("classes:class_detail"))
        self.assertTemplateUsed(response, "classes_detail/class_detail.html")
        self.assertEqual(list(response.context["students"]), [])

    def test_htmx_returns_active_students_of_selected_class(self):
        response = self.client.get(
            reverse("classes:class_detail"),
            {"school_class": self.school_class.pk},
            HTTP_HX_REQUEST="true",
        )
        self.assertTemplateUsed(response, "classes/partials/class_detail_table.html")
        self.assertEqual(list(response.context["students"]), [self.ana])

    def test_page_lists_classes_of_selected_year(self):
        response = self.client.get(
            reverse("classes:class_detail"), {"school_year": self.school_year.pk}
        )
        self.assertCountEqual(response.context["classes"], self.year_classes)

    def test_class_options_are_filtered_by_year_and_clear_the_table(self):
        response = self.client.get(
            reverse("classes:class_options"),
            {"school_year": self.school_year.pk},
            HTTP_HX_REQUEST="true",
        )
        self.assertTemplateUsed(response, "classes/partials/class_select.html")
        self.assertCountEqual(response.context["classes"], self.year_classes)
        self.assertContains(response, 'hx-swap-oob="true"')
        self.assertEqual(
            response["HX-Push-Url"],
            f"{reverse('classes:class_detail')}?school_year={self.school_year.pk}",
        )
