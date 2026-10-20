from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class LoginViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="secretaria", password="s3nha-forte")

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
