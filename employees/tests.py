from django.urls import reverse

from base.testing import LoggedInTestCase
from employees.models import Employee, EmployeeRoleType


class EmployeeRoleViewTests(LoggedInTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher_role = EmployeeRoleType.objects.create(role="Professor")
        cls.unused_role = EmployeeRoleType.objects.create(role="Porteiro")
        Employee.objects.create(
            name="Carlos Melo",
            cpf="98765432101",
            rg="5432101",
            issuing_authority="SSP",
            role=cls.teacher_role,
        )

    def test_create_flashes_message(self):
        response = self.client.post(
            reverse("employees:employee_role_add"), {"role": "Secretário"}, follow=True
        )
        self.assertRedirects(response, reverse("employees:employee_role_list"))
        self.assertContains(response, "Registro cadastrado com sucesso")

    def test_role_in_use_is_not_deleted(self):
        response = self.client.post(
            reverse("employees:employee_role_delete", args=[self.teacher_role.pk]),
            follow=True,
        )
        self.assertTrue(
            EmployeeRoleType.objects.filter(pk=self.teacher_role.pk).exists()
        )
        self.assertContains(response, "está em uso")

    def test_unused_role_is_deleted(self):
        response = self.client.post(
            reverse("employees:employee_role_delete", args=[self.unused_role.pk]),
            follow=True,
        )
        self.assertFalse(
            EmployeeRoleType.objects.filter(pk=self.unused_role.pk).exists()
        )
        self.assertContains(response, "Registro deletado com sucesso")
