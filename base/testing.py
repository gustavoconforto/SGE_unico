from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext


class LoggedInTestCase(TestCase):
    """TestCase whose client is logged in, since every view requires login."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.login_user = User.objects.create_user(username="test-login")

    def setUp(self):
        self.client.force_login(self.login_user)

    def assertQueriesDontGrow(self, url, add_rows):
        """Fail on N+1: a list's query count must not change when rows are added.
        Call it with at least one row already on the page."""
        self.client.get(url)  # warm per-process caches (content types, session)
        with CaptureQueriesContext(connection) as before:
            self.client.get(url)
        add_rows()
        with CaptureQueriesContext(connection) as after:
            response = self.client.get(url)
        self.assertEqual(
            len(after),
            len(before),
            f"{url} ran {len(before)} queries, then {len(after)} after adding rows",
        )
        return response
