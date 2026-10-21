from decimal import Decimal

from django.urls import reverse

from base.testing import LoggedInTestCase
from incidents.models import Incident, IncidentType
from students.models import Student

HTMX = {"HTTP_HX_REQUEST": "true"}


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
        student = Student.objects.create(
            name="Ana Souza", cpf="12345678901", rg="1234567", issuing_authority="SSP"
        )
        Incident.objects.create(incident_type=incident_type, student=student)
        response = self.client.post(
            reverse("incidents:incident_type_delete", args=[incident_type.pk])
        )
        self.assertRedirects(response, reverse("incidents:incident_type_list"))
        self.assertTrue(IncidentType.objects.filter(pk=incident_type.pk).exists())


class IncidentViewsTests(LoggedInTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = Student.objects.create(
            name="Ana Souza", cpf="12345678901", rg="1234567", issuing_authority="SSP"
        )
        cls.late = IncidentType.objects.create(type="Atraso", penalty=Decimal("0.5"))
        cls.fight = IncidentType.objects.create(type="Briga", penalty=Decimal("2.0"))

    def test_crud(self):
        response = self.client.post(
            reverse("incidents:incident_add"),
            {"student": self.student.pk, "incident_type": self.late.pk},
        )
        self.assertRedirects(response, reverse("incidents:incident_list"))
        incident = Incident.objects.get()

        response = self.client.post(
            reverse("incidents:incident_edit", args=[incident.pk]),
            {"student": self.student.pk, "incident_type": self.fight.pk},
        )
        self.assertRedirects(response, reverse("incidents:incident_list"))
        incident.refresh_from_db()
        self.assertEqual(incident.incident_type, self.fight)

        response = self.client.get(
            reverse("incidents:incident_list"), {"q": "ana"}, **HTMX
        )
        self.assertTemplateUsed(response, "incidents/partials/incident_table.html")
        self.assertContains(response, "Briga")

        self.client.post(reverse("incidents:incident_delete", args=[incident.pk]))
        self.assertFalse(Incident.objects.exists())

    def test_list_page_renders(self):
        response = self.client.get(reverse("incidents:incident_list"))
        self.assertTemplateUsed(response, "incidents/incident_list.html")
        self.assertContains(response, "Ocorrências")
