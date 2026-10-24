from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse

from base.testing import LoggedInTestCase
from classes.models import Class
from enrollments.models import (
    Enrollment,
    EnrollmentStatus,
    EnrollmentType,
    SchoolYear,
)
from grades.models import ExamType, Grade, GradeLevelSubject, Subject
from incidents.forms import IncidentForm
from incidents.models import (
    BathroomPermission,
    Incident,
    IncidentType,
    StudentDelay,
    StudentDelayType,
)
from incidents.services import concept_grades
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

    def test_list_filters_by_date_range(self):
        for day in (1, 10, 20):
            StudentDelay.objects.create(
                enrollment=self.enrollment,
                delay_type=StudentDelayType.ACCEPTABLE,
                incident_date=date(2027, 3, day),
            )
        url = reverse("incidents:student_delay_list")

        def listed(params):
            response = self.client.get(url, params, **HTMX)
            self.assertTemplateUsed(
                response, "student_delays/partials/student_delay_table.html"
            )
            return [
                delay.incident_date.day for delay in response.context["student_delays"]
            ]

        both_ends = {"date_from": "2027-03-01", "date_to": "2027-03-10"}
        self.assertEqual(listed(both_ends), [10, 1])
        self.assertEqual(listed({"date_from": "2027-03-10"}), [20, 10])
        self.assertEqual(listed({"date_to": "2027-03-09"}), [1])
        self.assertEqual(listed({"q": "ana", **both_ends}), [10, 1])
        self.assertEqual(listed({"q": "bruno", **both_ends}), [])


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


class ConceptGradeTests(LoggedInTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.enrollment = create_enrollment()
        school_year = cls.enrollment.enrollment_type.school_year
        school_year.bi_1_begins = date(2027, 2, 1)
        school_year.bi_1_ends = date(2027, 4, 15)
        school_year.save()
        cls.other = Enrollment.objects.create(
            student=Student.objects.create(
                name="Bruno Lima",
                cpf="12345678902",
                rg="7654321",
                issuing_authority="SSP",
            ),
            enrollment_type=cls.enrollment.enrollment_type,
            school_class=cls.enrollment.school_class,
        )
        cls.math = Subject.objects.create(name="Matemática")
        cls.history = Subject.objects.create(name="História")
        GradeLevelSubject.objects.create(grade_level=1, subject=cls.math)
        GradeLevelSubject.objects.create(grade_level=1, subject=cls.history)
        cls.concept = ExamType.objects.create(
            name="Conceito", code="C", max_score=Decimal(1)
        )
        cls.light = IncidentType.objects.create(type="Conversa", penalty=Decimal("0.3"))

    def setUp(self):
        super().setUp()
        # The fixtures' school year is 2027
        today = patch("django.utils.timezone.localdate", return_value=date(2027, 3, 1))
        today.start()
        self.addCleanup(today.stop)

    def enrollment_in_year(self, year, name, cpf, rg, **kwargs):
        school_year = SchoolYear.objects.create(
            begins=date(year, 1, 10),
            ends=date(year, 12, 15),
            bi_1_begins=date(year, 2, 1),
            bi_1_ends=date(year, 4, 15),
        )
        program = self.enrollment.enrollment_type.program
        return Enrollment.objects.create(
            student=Student.objects.create(
                name=name, cpf=cpf, rg=rg, issuing_authority="SSP"
            ),
            enrollment_type=EnrollmentType.objects.create(
                program=program,
                school_year=school_year,
                total_price=Decimal("1000.00"),
            ),
            school_class=Class.objects.create(
                program=program, year=school_year, name="A", grade_level=1
            ),
            **kwargs,
        )

    def incident(self, day, enrollment=None):
        Incident.objects.create(
            incident_type=self.light,
            enrollment=enrollment or self.enrollment,
            incident_date=day,
        )

    def delays(self, count, delay_type=StudentDelayType.ACCEPTABLE, day=None):
        for _ in range(count):
            StudentDelay.objects.create(
                enrollment=self.enrollment,
                delay_type=delay_type,
                incident_date=day or date(2027, 3, 1),
            )

    def concept_scores(self, enrollment):
        return sorted(
            Grade.objects.filter(
                enrollment=enrollment, exam_type=self.concept, bimester=1
            ).values_list("score", flat=True)
        )

    def test_penalties_and_extra_tolerated_delays_in_the_bimester(self):
        self.incident(date(2027, 3, 1))
        self.incident(date(2027, 5, 1))  # outside the bimester
        self.delays(3)  # one beyond the two tolerated
        self.delays(2, delay_type=StudentDelayType.UNACCEPTABLE)
        self.delays(2, day=date(2027, 6, 1))  # outside the bimester
        grades = concept_grades([self.enrollment, self.other], 1)
        self.assertEqual(grades[self.enrollment.pk], Decimal("0.5"))
        self.assertEqual(grades[self.other.pk], Decimal(1))

    def test_never_below_zero(self):
        for day in (1, 2, 3, 4):
            self.incident(date(2027, 3, day))
        self.assertEqual(concept_grades([self.enrollment], 1)[self.enrollment.pk], 0)

    def test_bimester_without_dates_is_skipped(self):
        self.assertEqual(concept_grades([self.enrollment], 2), {})

    def test_individual_calculates_every_subject(self):
        url = reverse("incidents:incident_grades_individual")
        params = {"enrollment": self.enrollment.pk, "bimester": 1}
        Grade.objects.create(
            enrollment=self.enrollment,
            subject=self.math,
            exam_type=self.concept,
            bimester=1,
            score=Decimal(1),
        )
        self.incident(date(2027, 3, 1))

        response = self.client.get(url, params, **HTMX)
        self.assertTemplateUsed(
            response, "incident_grades/partials/incident_grades_subjects.html"
        )
        self.assertContains(response, "História")
        self.assertContains(response, "Calcular")

        response = self.client.post(f"{url}?enrollment={self.enrollment.pk}&bimester=1")
        self.assertRedirects(
            response, f"{url}?enrollment={self.enrollment.pk}&bimester=1"
        )
        self.assertEqual(
            self.concept_scores(self.enrollment), [Decimal("0.7"), Decimal("0.7")]
        )
        self.assertEqual(self.concept_scores(self.other), [])

    def test_all_calculates_only_the_current_year(self):
        url = reverse("incidents:incident_grades_all")
        self.incident(date(2027, 3, 1), enrollment=self.other)
        dropped = Enrollment.objects.create(
            student=Student.objects.create(
                name="Caio Dias",
                cpf="12345678903",
                rg="7654322",
                issuing_authority="SSP",
            ),
            enrollment_type=self.enrollment.enrollment_type,
            school_class=self.enrollment.school_class,
            status=EnrollmentStatus.DROPPED,
        )
        next_year = self.enrollment_in_year(
            2028, "Davi Rocha", "12345678904", "7654323"
        )
        last_year = self.enrollment_in_year(
            2026,
            "Eva Melo",
            "12345678905",
            "7654324",
            status=EnrollmentStatus.COMPLETED,
        )

        response = self.client.get(url, {"bimester": 1})
        self.assertContains(response, "Ano letivo 2027")
        self.assertContains(response, "Ana Souza")
        self.assertNotContains(response, "Davi Rocha")
        self.assertNotContains(response, "Eva Melo")

        response = self.client.post(url, {"bimester": 1})
        self.assertRedirects(response, f"{url}?bimester=1")
        self.assertEqual(self.concept_scores(self.enrollment), [Decimal(1)] * 2)
        self.assertEqual(self.concept_scores(self.other), [Decimal("0.7")] * 2)
        self.assertEqual(self.concept_scores(dropped), [])
        self.assertEqual(self.concept_scores(next_year), [])
        self.assertEqual(self.concept_scores(last_year), [])

        response = self.client.get(url, {"bimester": 1, "q": "bruno"}, **HTMX)
        self.assertTemplateUsed(
            response, "incident_grades/partials/incident_grades_table.html"
        )
        self.assertContains(response, "0,70")
        self.assertNotContains(response, "Ana Souza")

    def test_all_without_a_school_year_for_today(self):
        url = reverse("incidents:incident_grades_all")
        with patch("django.utils.timezone.localdate", return_value=date(2029, 3, 1)):
            response = self.client.get(url, {"bimester": 1})
            self.assertContains(response, "Cadastre o ano letivo de 2029")
            self.assertNotContains(response, "Ana Souza")
            self.assertNotContains(response, "Calcular")

            response = self.client.post(url, {"bimester": 1}, follow=True)
        self.assertContains(response, "Cadastre o ano letivo de 2029")
        self.assertEqual(self.concept_scores(self.enrollment), [])
