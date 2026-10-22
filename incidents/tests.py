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
from incidents.forms import IncidentForm
from incidents.models import (
    BathroomPermission,
    Incident,
    IncidentType,
    StudentDelay,
    StudentDelayType,
)
from programs.models import Program
from students.models import Student

HTMX = {"HTTP_HX_REQUEST": "true"}


def create_enrollment(name="Ana Souza", cpf="12345678901", **kwargs):
    school_year = SchoolYear.objects.create(
        begins=date(2027, 1, 10), ends=date(2027, 12, 15)
    )
    program = Program.objects.create(name="Ensino Médio")
    enrollment_type = EnrollmentType.objects.create(
        program=program, school_year=school_year, total_price=Decimal("1000.00")
    )
    school_class = Class.objects.create(
        program=program, year=school_year, name="A", grade_level=1
    )
    student = Student.objects.create(
        name=name, cpf=cpf, rg="1234567", issuing_authority="SSP"
    )
    return Enrollment.objects.create(
        student=student,
        enrollment_type=enrollment_type,
        school_class=school_class,
        **kwargs,
    )


class IncidentTypeViewsTests(LoggedInTestCase):
    def test_crud(self):
        response = self.client.post(
            reverse("incidents:incident_type_add"),
            {"type": "Atraso", "penalty": "0.5"},
        )
        self.assertRedirects(response, reverse("incidents:incident_type_list"))
        incident_type = IncidentType.objects.get()

        response = self.client.post(
            reverse("incidents:incident_type_edit", args=[incident_type.pk]),
            {"type": "Atraso recorrente", "penalty": "1.0"},
        )
        self.assertRedirects(response, reverse("incidents:incident_type_list"))
        incident_type.refresh_from_db()
        self.assertEqual(incident_type.type, "Atraso recorrente")
        self.assertEqual(incident_type.penalty, Decimal("1.0"))

        response = self.client.get(
            reverse("incidents:incident_type_list"), {"q": "recorrente"}, **HTMX
        )
        self.assertTemplateUsed(
            response, "incident_types/partials/incident_type_table.html"
        )
        self.assertContains(response, "Atraso recorrente")

        self.client.post(
            reverse("incidents:incident_type_delete", args=[incident_type.pk])
        )
        self.assertFalse(IncidentType.objects.exists())

    def test_penalty_cannot_be_negative(self):
        response = self.client.post(
            reverse("incidents:incident_type_add"),
            {"type": "Atraso", "penalty": "-1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(IncidentType.objects.exists())

    def test_delete_blocked_when_type_has_incidents(self):
        incident_type = IncidentType.objects.create(type="Atraso", penalty=1)
        Incident.objects.create(
            incident_type=incident_type,
            enrollment=create_enrollment(),
            incident_date=date(2027, 3, 1),
        )
        response = self.client.post(
            reverse("incidents:incident_type_delete", args=[incident_type.pk])
        )
        self.assertRedirects(response, reverse("incidents:incident_type_list"))
        self.assertTrue(IncidentType.objects.filter(pk=incident_type.pk).exists())


class IncidentViewsTests(LoggedInTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.enrollment = create_enrollment()
        cls.late = IncidentType.objects.create(type="Atraso", penalty=Decimal("0.5"))
        cls.fight = IncidentType.objects.create(type="Briga", penalty=Decimal("2.0"))

    def test_crud(self):
        response = self.client.post(
            reverse("incidents:incident_add"),
            {
                "enrollment": self.enrollment.pk,
                "incident_type": self.late.pk,
                "incident_date": "2027-03-01",
            },
        )
        self.assertRedirects(response, reverse("incidents:incident_list"))
        incident = Incident.objects.get()

        response = self.client.post(
            reverse("incidents:incident_edit", args=[incident.pk]),
            {
                "enrollment": self.enrollment.pk,
                "incident_type": self.fight.pk,
                "incident_date": "2027-03-01",
            },
        )
        self.assertRedirects(response, reverse("incidents:incident_list"))
        incident.refresh_from_db()
        self.assertEqual(incident.incident_type, self.fight)

        response = self.client.get(
            reverse("incidents:incident_list"), {"q": "ana"}, **HTMX
        )
        self.assertTemplateUsed(response, "incidents/partials/incident_table.html")
        self.assertContains(response, "Briga")
        self.assertContains(response, str(self.enrollment.school_class))

        self.client.post(reverse("incidents:incident_delete", args=[incident.pk]))
        self.assertFalse(Incident.objects.exists())

    def test_list_page_renders(self):
        response = self.client.get(reverse("incidents:incident_list"))
        self.assertTemplateUsed(response, "incidents/incident_list.html")
        self.assertContains(response, "Ocorrências")

    def test_form_lists_only_active_enrollments(self):
        self.enrollment.status = EnrollmentStatus.DROPPED
        self.enrollment.save()
        self.assertNotIn(self.enrollment, IncidentForm().fields["enrollment"].queryset)

        incident = Incident.objects.create(
            incident_type=self.late,
            enrollment=self.enrollment,
            incident_date=date(2027, 3, 1),
        )
        self.assertIn(
            self.enrollment,
            IncidentForm(instance=incident).fields["enrollment"].queryset,
        )


class StudentDelayViewsTests(LoggedInTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.enrollment = create_enrollment()

    def test_crud(self):
        response = self.client.post(
            reverse("incidents:student_delay_add"),
            {
                "enrollment": self.enrollment.pk,
                "delay_type": StudentDelayType.ACCEPTABLE,
                "incident_date": "2027-03-01",
            },
        )
        self.assertRedirects(response, reverse("incidents:student_delay_list"))
        delay = StudentDelay.objects.get()

        response = self.client.post(
            reverse("incidents:student_delay_edit", args=[delay.pk]),
            {
                "enrollment": self.enrollment.pk,
                "delay_type": StudentDelayType.UNACCEPTABLE,
                "incident_date": "2027-03-01",
            },
        )
        self.assertRedirects(response, reverse("incidents:student_delay_list"))
        delay.refresh_from_db()
        self.assertEqual(delay.delay_type, StudentDelayType.UNACCEPTABLE)

        response = self.client.get(
            reverse("incidents:student_delay_list"), {"q": "ana"}, **HTMX
        )
        self.assertTemplateUsed(
            response, "student_delays/partials/student_delay_table.html"
        )
        self.assertContains(response, "Não tolerado")

        self.client.post(reverse("incidents:student_delay_delete", args=[delay.pk]))
        self.assertFalse(StudentDelay.objects.exists())

    def test_list_page_renders(self):
        response = self.client.get(reverse("incidents:student_delay_list"))
        self.assertTemplateUsed(response, "student_delays/student_delay_list.html")
        self.assertContains(response, "Atrasos")


class BathroomPermissionViewsTests(LoggedInTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.enrollment = create_enrollment()

    def test_crud(self):
        response = self.client.post(
            reverse("incidents:bathroom_permission_add"),
            {
                "enrollment": self.enrollment.pk,
                "class_period": 2,
                "incident_date": "2027-03-01",
            },
        )
        self.assertRedirects(response, reverse("incidents:bathroom_permission_list"))
        permission = BathroomPermission.objects.get()

        response = self.client.post(
            reverse("incidents:bathroom_permission_edit", args=[permission.pk]),
            {
                "enrollment": self.enrollment.pk,
                "class_period": 3,
                "incident_date": "2027-03-02",
            },
        )
        self.assertRedirects(response, reverse("incidents:bathroom_permission_list"))
        permission.refresh_from_db()
        self.assertEqual(permission.class_period, 3)

        response = self.client.get(
            reverse("incidents:bathroom_permission_list"), {"q": "ana"}, **HTMX
        )
        self.assertTemplateUsed(
            response, "bathroom_permissions/partials/bathroom_permission_table.html"
        )
        self.assertContains(response, "3º")
        self.assertContains(response, "02/03/2027")

        self.client.post(
            reverse("incidents:bathroom_permission_delete", args=[permission.pk])
        )
        self.assertFalse(BathroomPermission.objects.exists())

    def test_class_period_must_be_positive(self):
        response = self.client.post(
            reverse("incidents:bathroom_permission_add"),
            {
                "enrollment": self.enrollment.pk,
                "class_period": 0,
                "incident_date": "2027-03-01",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(BathroomPermission.objects.exists())

    def test_list_page_renders(self):
        response = self.client.get(reverse("incidents:bathroom_permission_list"))
        self.assertTemplateUsed(
            response, "bathroom_permissions/bathroom_permission_list.html"
        )
        self.assertContains(response, "Saídas para banheiro")
