from datetime import date
from io import StringIO

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.management import call_command
from django.template import Context, Template
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Payment, Supplier
from billing.models import BankSlip, ReturnEvent, SlipStatus
from classes.models import Class
from enrollments.models import Enrollment
from grades.models import Grade
from lessons.models import Lecture, TimetableSlot
from pathways.models import PathwayAttendance, PathwayEnrollment, PathwayGrade
from students.models import Student

from .testing import LoggedInTestCase


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

    def test_logged_in_user_is_sent_away_from_login(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("login"))
        self.assertRedirects(response, reverse("base:main"))


class LoginRequiredTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="secretaria", password="s3nha-forte"
        )

    def test_anonymous_user_is_redirected_to_login(self):
        url = reverse("accounts:supplier_list")
        response = self.client.get(url)
        self.assertRedirects(response, f"{reverse('login')}?next={url}")

    def test_anonymous_htmx_request_gets_full_page_redirect(self):
        url = reverse("accounts:supplier_list")
        response = self.client.get(url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["HX-Redirect"], f"{reverse('login')}?next={url}")

    def test_logged_in_user_sees_logout_in_sidebar(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("base:main"))
        self.assertContains(response, f'action="{reverse("logout")}"')

    def test_logout_ends_session(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))
        response = self.client.get(reverse("base:main"))
        self.assertRedirects(response, f"{reverse('login')}?next=/")


class FullSeedTests(TestCase):
    def test_today_option_fills_a_future_school_year(self):
        # --today makes a year that hasn't started look under way.
        year = timezone.localdate().year + 1
        call_command(
            "full_seed",
            reset=False,
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
            reset=False,
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
        # Every class gets all of its weekly periods, and a diary from them.
        self.assertEqual(TimetableSlot.objects.count(), 31 * 27)
        self.assertTrue(Lecture.objects.exists())
        self.assertTrue(PathwayEnrollment.objects.exists())
        self.assertTrue(PathwayAttendance.objects.exists())
        self.assertTrue(PathwayGrade.objects.exists())
        # The extra grade is calculated for every enrollment, zero included.
        self.assertTrue(Grade.objects.filter(exam_type__code="EX").exists())


class UiTagsTests(TestCase):
    def render(self, source, path="/", **context):
        request = RequestFactory().get(path)
        return Template("{% load ui %}" + source).render(
            Context({"request": request, **context})
        )

    def test_nav_active_matches_the_list_and_its_resource_pages(self):
        source = "{% nav_active url as active %}{{ active }}"
        url = "/accounts/suppliers/list/"
        for path, expected in [
            ("/accounts/suppliers/list/", "True"),
            ("/accounts/suppliers/edit/3/", "True"),
            ("/accounts/suppliers/add/", "True"),
            ("/accounts/categories/list/", "False"),
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.render(source, path, url=url), expected)

    def test_nav_active_ignores_sibling_resources_under_the_same_app(self):
        # /pathways/list/ must not light up on /pathways/offerings/edit/1/.
        source = "{% nav_active url as active %}{{ active }}"
        self.assertEqual(
            self.render(source, "/pathways/offerings/edit/1/", url="/pathways/list/"),
            "False",
        )

    def test_document_formats_cpf_and_cnpj(self):
        source = "{{ value|document }}|{{ value|person_kind }}"
        self.assertEqual(
            self.render(source, value="12345678909"), "123.456.789-09|Pessoa física"
        )
        self.assertEqual(
            self.render(source, value="12345678000190"),
            "12.345.678/0001-90|Pessoa jurídica",
        )
        self.assertEqual(self.render(source, value=""), "|")

    def test_active_filter_count(self):
        class FilterForm(forms.Form):
            status = forms.CharField(required=False)
            year = forms.CharField(required=False)

        source = "{{ form|active_filter_count }}"
        self.assertEqual(self.render(source, form=FilterForm()), "0")
        self.assertEqual(
            self.render(source, form=FilterForm({"status": "A", "year": ""})), "1"
        )

    def test_optional_marker_only_on_model_forms(self):
        class PickerForm(forms.Form):
            school_class = forms.CharField(required=False)

        class UserForm(forms.ModelForm):
            class Meta:
                model = User
                fields = ("email",)

        source = "{% include 'components/form/field.html' with field=field %}"
        self.assertNotIn(
            "(opcional)", self.render(source, field=PickerForm()["school_class"])
        )
        self.assertIn("(opcional)", self.render(source, field=UserForm()["email"]))


class LayoutTests(LoggedInTestCase):
    def test_sidebar_marks_the_current_section(self):
        response = self.client.get(reverse("accounts:supplier_list"))
        self.assertContains(
            response,
            f'href="{reverse("accounts:supplier_list")}" class="nav-link active" aria-current="page"',
        )

    def test_page_title_names_the_browser_tab(self):
        response = self.client.get(reverse("accounts:supplier_list"))
        self.assertContains(response, "<title>Fornecedores</title>")


class UserAddTests(LoggedInTestCase):
    def test_new_user_can_log_in_with_the_password_given(self):
        response = self.client.post(
            reverse("base:user_add"),
            {
                "username": "joana",
                "first_name": "Joana",
                "password1": "Cad3rno-azul",
                "password2": "Cad3rno-azul",
            },
        )
        self.assertRedirects(response, reverse("base:user_list"))
        self.client.logout()
        self.assertTrue(self.client.login(username="joana", password="Cad3rno-azul"))

    def test_passwords_must_match(self):
        response = self.client.post(
            reverse("base:user_add"),
            {"username": "joana", "password1": "Cad3rno-azul", "password2": "outra"},
        )
        self.assertIn("password2", response.context["form"].errors)
        self.assertFalse(User.objects.filter(username="joana").exists())


class UserEditStatusTests(LoggedInTestCase):
    def test_non_superuser_save_keeps_status_flags(self):
        user = User.objects.create_user(
            username="ana", is_staff=True, is_superuser=True
        )
        self.client.post(
            reverse("base:user_edit", args=[user.pk]),
            {"username": "ana", "first_name": "Ana", "is_superuser": "false"},
        )
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Ana")
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_superuser)

    def test_superuser_can_change_status_flags(self):
        self.client.force_login(
            User.objects.create_user(username="admin", is_superuser=True)
        )
        user = User.objects.create_user(username="ana")
        self.client.post(
            reverse("base:user_edit", args=[user.pk]),
            {"username": "ana", "is_active": "false", "is_staff": "true"},
        )
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertTrue(user.is_staff)


class CpfValidationTests(TestCase):
    def test_cpf_must_have_eleven_digits(self):
        for cpf in ("1234", "123.456.789", "1234567890a"):
            with self.subTest(cpf=cpf):
                student = Student(name="Ana", cpf=cpf, rg="1", issuing_authority="SSP")
                with self.assertRaises(ValidationError) as caught:
                    student.full_clean()
                self.assertIn("cpf", caught.exception.message_dict)


class UserEditTests(LoggedInTestCase):
    def test_invalid_post_keeps_errors_and_input(self):
        user = User.objects.create_user(username="ana")
        response = self.client.post(
            reverse("base:user_edit", args=[user.pk]),
            {"username": "", "first_name": "Ana Maria"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertContains(response, "Ana Maria")
        user.refresh_from_db()
        self.assertEqual(user.username, "ana")


class PageSmokeTests(LoggedInTestCase):
    """Every screen renders against seeded data: list, add, edit, delete and
    detail pages of each app, reached through the URLconf."""

    @classmethod
    def setUpTestData(cls):
        call_command(
            "full_seed",
            reset=False,
            students_per_class=1,
            year=timezone.localdate().year - 1,
            stdout=StringIO(),
        )

    def iter_urls(self):
        from django.urls import get_resolver
        from django.urls.resolvers import URLResolver

        def walk(patterns, namespace=None):
            for p in patterns:
                if isinstance(p, URLResolver):
                    yield from walk(p.url_patterns, p.namespace or namespace)
                elif namespace and namespace != "admin" and p.name:
                    yield namespace, p

        yield from walk(get_resolver().url_patterns)

    def test_pages_render(self):
        checked = 0
        for namespace, pattern in self.iter_urls():
            converters = pattern.pattern.converters
            view_class = getattr(pattern.callback, "view_class", None)
            model = getattr(view_class, "model", None)
            if converters:
                if list(converters) != ["pk"] or model is None:
                    continue
                view = view_class()
                view.request = RequestFactory().get("/")
                view.request.user = self.login_user
                view.kwargs = {}
                try:
                    queryset = view.get_queryset()
                except AttributeError, KeyError, ImproperlyConfigured:
                    # Views that filter on URL kwargs or other request state.
                    queryset = model._default_manager.all()
                obj = queryset.order_by("pk").first()
                if obj is None:
                    continue
                url = reverse(f"{namespace}:{pattern.name}", args=[obj.pk])
            else:
                url = reverse(f"{namespace}:{pattern.name}")
            if any(
                word in url
                for word in (
                    "download",
                    "pdf",
                    "preview",
                    "report",
                    "options",
                    "lookup",
                )
            ):
                continue
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertIn(response.status_code, (200, 302, 405))
                checked += 1
        self.assertGreater(checked, 80)


class SeedTests(TestCase):
    def test_seeds_people_without_enrollments(self):
        call_command("seed", reset=False, students_per_class=1, stdout=StringIO())
        self.assertEqual(Student.objects.count(), 31)
        self.assertFalse(
            Student.objects.filter(registration__startswith="TMP").exists()
        )
        self.assertEqual(Enrollment.objects.count(), 0)
        self.assertEqual(Class.objects.filter(capacity=45).count(), 31)
        self.assertTrue(Supplier.objects.exists())
