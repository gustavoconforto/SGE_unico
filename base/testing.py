from django.contrib.auth.models import User
from django.test import TestCase


class LoggedInTestCase(TestCase):
    """TestCase whose client is logged in, since every view requires login."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.login_user = User.objects.create_user(username="test-login")

    def setUp(self):
        self.client.force_login(self.login_user)
