from datetime import date

from django.urls import reverse

from base.testing import LoggedInTestCase
from enrollments.models import EnrollmentStatus
from grades.models import Subject
from incidents.tests import create_enrollment
from q_and_a.forms import QandAForm
from q_and_a.models import QandA

HTMX = {"HTTP_HX_REQUEST": "true"}


class QandAViewsTests(LoggedInTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.enrollment = create_enrollment()
        cls.math = Subject.objects.create(name="Matemática")
        cls.physics = Subject.objects.create(name="Física")

    def test_crud(self):
        response = self.client.post(
            reverse("q_and_a:q_and_a_add"),
            {
                "enrollment": self.enrollment.pk,
                "subject": self.math.pk,
                "q_and_a_date": "2027-03-01",
            },
        )
        self.assertRedirects(response, reverse("q_and_a:q_and_a_list"))
        q_and_a = QandA.objects.get()
        self.assertEqual(str(q_and_a), f"{self.enrollment.student} - Matemática")

        response = self.client.post(
            reverse("q_and_a:q_and_a_edit", args=[q_and_a.pk]),
            {
                "enrollment": self.enrollment.pk,
                "subject": self.physics.pk,
                "q_and_a_date": "2027-03-02",
            },
        )
        self.assertRedirects(response, reverse("q_and_a:q_and_a_list"))
        q_and_a.refresh_from_db()
        self.assertEqual(q_and_a.subject, self.physics)
        self.assertEqual(q_and_a.q_and_a_date, date(2027, 3, 2))

        response = self.client.get(
            reverse("q_and_a:q_and_a_list"), {"q": "ana"}, **HTMX
        )
        self.assertTemplateUsed(response, "q_and_as/partials/q_and_a_table.html")
        self.assertContains(response, "Física")

        response = self.client.get(reverse("q_and_a:q_and_a_delete", args=[q_and_a.pk]))
        self.assertContains(response, "Física")
        self.client.post(reverse("q_and_a:q_and_a_delete", args=[q_and_a.pk]))
        self.assertFalse(QandA.objects.exists())

    def test_list_page_renders(self):
        response = self.client.get(reverse("q_and_a:q_and_a_list"))
        self.assertTemplateUsed(response, "q_and_as/q_and_a_list.html")
        self.assertContains(response, "Plantões")

    def test_add_page_renders(self):
        response = self.client.get(reverse("q_and_a:q_and_a_add"))
        self.assertTemplateUsed(response, "q_and_as/q_and_a_add.html")

    def test_list_searches_and_filters(self):
        for day, subject in ((1, self.math), (10, self.physics), (20, self.math)):
            QandA.objects.create(
                enrollment=self.enrollment,
                subject=subject,
                q_and_a_date=date(2027, 3, day),
            )
        url = reverse("q_and_a:q_and_a_list")

        def listed(params):
            response = self.client.get(url, params, **HTMX)
            self.assertTemplateUsed(response, "q_and_as/partials/q_and_a_table.html")
            return [item.q_and_a_date.day for item in response.context["q_and_as"]]

        self.assertEqual(listed({}), [20, 10, 1])
        self.assertEqual(listed({"q": "física"}), [10])
        self.assertEqual(listed({"subject": self.math.pk}), [20, 1])
        both_ends = {"date_from": "2027-03-01", "date_to": "2027-03-10"}
        self.assertEqual(listed(both_ends), [10, 1])
        self.assertEqual(listed({"subject": self.math.pk, **both_ends}), [1])
        self.assertEqual(listed({"q": "bruno", **both_ends}), [])

    def test_form_lists_only_active_enrollments(self):
        self.enrollment.status = EnrollmentStatus.DROPPED
        self.enrollment.save()
        self.assertNotIn(self.enrollment, QandAForm().fields["enrollment"].queryset)

        q_and_a = QandA.objects.create(
            enrollment=self.enrollment,
            subject=self.math,
            q_and_a_date=date(2027, 3, 1),
        )
        self.assertIn(
            self.enrollment,
            QandAForm(instance=q_and_a).fields["enrollment"].queryset,
        )
