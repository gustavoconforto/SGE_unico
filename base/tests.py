from datetime import date
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Payment
from billing.models import BankSlip, ReturnEvent, SlipStatus
from classes.models import Class
from enrollments.models import Enrollment
from grades.models import Grade
from students.models import Student


class LoginViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="secretaria", password="s3nha-forte"
        )

    def test_login_page_renders(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "login/login.html")

    def test_valid_login_redirects_to_main(self):
        response = self.client.post(
            reverse("login"), {"username": "secretaria", "password": "s3nha-forte"}
        )
        self.assertRedirects(response, reverse("base:main"))

    def test_invalid_login_shows_error(self):
        response = self.client.post(
            reverse("login"), {"username": "secretaria", "password": "errada"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].non_field_errors())


class FullSeedTests(TestCase):
    def test_today_option_fills_a_future_school_year(self):
        # --today makes a year that hasn't started look under way.
        year = timezone.localdate().year + 1
        call_command(
            "full_seed",
            students_per_class=2,
            year=year,
            today=date(year, 11, 20),
            stdout=StringIO(),
        )
        self.assertTrue(Grade.objects.filter(exam_type__code="PB").exists())
        self.assertTrue(BankSlip.objects.filter(status=SlipStatus.PAID).exists())

    def test_fills_a_past_school_year(self):
        # A past year runs every step: all bimesters graded, every month billed.
        call_command(
            "full_seed",
            students_per_class=2,
            year=timezone.localdate().year - 1,
            stdout=StringIO(),
        )
        self.assertEqual(Class.objects.count(), 31)
        self.assertEqual(Student.objects.count(), 62)
        self.assertEqual(Enrollment.objects.count(), 62)
        self.assertTrue(Grade.objects.filter(exam_type__code="PB").exists())
        self.assertTrue(BankSlip.objects.filter(status=SlipStatus.PAID).exists())
        self.assertFalse(ReturnEvent.objects.filter(status="E").exists())
        self.assertTrue(
            Payment.objects.filter(
                installment__account__supplier__isnull=False
            ).exists()
        )
