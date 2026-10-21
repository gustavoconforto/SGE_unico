from django.urls import reverse

from base.testing import LoggedInTestCase
from departments.models import Department
from employees.models import Employee, EmployeeRoleType
from grades.models import Subject


class DepartmentViewTests(LoggedInTestCase):
    @classmethod
    def setUpTestData(cls):
        role = EmployeeRoleType.objects.create(role="Professor")
        cls.teacher = Employee.objects.create(
            name="Carlos Melo",
            cpf="98765432101",
            rg="5432101",
            issuing_authority="SSP",
            role=role,
        )
        cls.exatas = Department.objects.create(name="Exatas")
        cls.exatas.teachers.add(cls.teacher)
        cls.humanas = Department.objects.create(name="Humanas")
        Subject.objects.create(name="Matemática", department=cls.exatas)

    def test_htmx_search_by_teacher_returns_partial_once_per_department(self):
        response = self.client.get(
            reverse("departments:department_list"),
            {"q": "Carlos"},
            HTTP_HX_REQUEST="true",
        )
        self.assertTemplateUsed(response, "departments/partials/department_table.html")
        self.assertEqual(list(response.context["departments"]), [self.exatas])
        self.assertContains(response, "Matemática")

    def test_create_with_teachers(self):
        response = self.client.post(
            reverse("departments:department_add"),
            {"name": "Linguagens", "teachers": [self.teacher.pk]},
            follow=True,
        )
        self.assertRedirects(response, reverse("departments:department_list"))
        self.assertContains(response, "Registro cadastrado com sucesso")
        department = Department.objects.get(name="Linguagens")
        self.assertEqual(list(department.teachers.all()), [self.teacher])

    def test_department_with_subjects_is_not_deleted(self):
        response = self.client.post(
            reverse("departments:department_delete", args=[self.exatas.pk]),
            follow=True,
        )
        self.assertTrue(Department.objects.filter(pk=self.exatas.pk).exists())
        self.assertContains(response, "possui matérias")

    def test_empty_department_is_deleted(self):
        self.client.post(
            reverse("departments:department_delete", args=[self.humanas.pk])
        )
        self.assertFalse(Department.objects.filter(pk=self.humanas.pk).exists())
