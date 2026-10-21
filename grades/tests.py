from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from classes.models import Class
from departments.models import Department
from employees.models import Employee, EmployeeRoleType
from enrollments.models import (
    Enrollment,
    EnrollmentStatus,
    EnrollmentType,
    SchoolYear,
)
from grades.models import ExamKind, ExamType, Grade, GradeLevelSubject, Subject
from grades.services import bimester_grade, final_average, report_card
from programs.models import Program
from students.models import Student


class GradeTestData(TestCase):
    @classmethod
    def setUpTestData(cls):
        school_year = SchoolYear.objects.create(
            begins=date(2027, 1, 10), ends=date(2027, 12, 15)
        )
        program = Program.objects.create(name="Ensino Médio")
        enrollment_type = EnrollmentType.objects.create(
            program=program,
            school_year=school_year,
            total_price=Decimal("1000.00"),
        )
        cls.school_class = Class.objects.create(
            program=program, year=school_year, name="A", grade_level=1
        )
        student = Student.objects.create(
            name="Ana Souza", cpf="12345678901", rg="5678901", issuing_authority="SSP"
        )
        cls.enrollment = Enrollment.objects.create(
            student=student,
            enrollment_type=enrollment_type,
            school_class=cls.school_class,
            enrolled_at=date(2027, 1, 15),
            due_day=10,
        )
        cls.math = Subject.objects.create(name="Matemática")
        cls.physics = Subject.objects.create(name="Física")
        cls.math_level_1 = GradeLevelSubject.objects.create(
            grade_level=1, subject=cls.math
        )
        GradeLevelSubject.objects.create(grade_level=2, subject=cls.physics)

        # The school's scheme: each exam's maximum is its share of the 10 points.
        cls.ps = ExamType.objects.create(
            name="Prova semanal", code="PS", max_score=Decimal(3)
        )
        cls.pb = ExamType.objects.create(
            name="Prova bimestral", code="PB", max_score=Decimal(6)
        )
        cls.behavior = ExamType.objects.create(
            name="Comportamento", code="COMP", max_score=Decimal(1)
        )
        cls.extra = ExamType.objects.create(
            name="Ponto extra",
            code="EX",
            kind=ExamKind.BONUS,
            max_score=Decimal(2),
        )
        cls.recovery = ExamType.objects.create(
            name="Recuperação", code="REC", kind=ExamKind.RECOVERY
        )

    def grade(self, exam_type, score, bimester=1, subject=None):
        return Grade(
            enrollment=self.enrollment,
            subject=subject or self.math,
            exam_type=exam_type,
            bimester=bimester,
            score=Decimal(score),
        )


class BimesterGradeTests(GradeTestData):
    def test_sum_of_the_exams(self):
        grades = [
            self.grade(self.ps, "2.5"),
            self.grade(self.pb, "4.75"),
            self.grade(self.behavior, "1"),
        ]
        self.assertEqual(bimester_grade(grades), Decimal("8.25"))

    def test_extra_points_are_added(self):
        grades = [
            self.grade(self.ps, "2"),
            self.grade(self.pb, "5"),
            self.grade(self.extra, "1.5"),
        ]
        self.assertEqual(bimester_grade(grades), Decimal("8.50"))

    def test_extra_points_cannot_pass_ten(self):
        grades = [
            self.grade(self.ps, "3"),
            self.grade(self.pb, "5.5"),
            self.grade(self.behavior, "1"),
            self.grade(self.extra, "2"),
        ]
        self.assertEqual(bimester_grade(grades), Decimal("10.00"))

    def test_recovery_replaces_the_grade_only_when_higher(self):
        self.assertEqual(
            bimester_grade([self.grade(self.pb, "4"), self.grade(self.recovery, "7")]),
            Decimal("7.00"),
        )
        self.assertEqual(
            bimester_grade([self.grade(self.pb, "5"), self.grade(self.recovery, "3")]),
            Decimal("5.00"),
        )

    def test_none_without_regular_grades(self):
        self.assertIsNone(bimester_grade([]))
        self.assertIsNone(bimester_grade([self.grade(self.extra, "1")]))


class FinalAverageTests(TestCase):
    def test_mean_of_four_bimesters_rounded_half_up(self):
        grades = [Decimal(6), Decimal(7), Decimal(8), Decimal("7.5")]
        self.assertEqual(final_average(grades), Decimal("7.13"))

    def test_none_while_a_bimester_is_missing(self):
        self.assertIsNone(final_average([Decimal(6), None, Decimal(8), Decimal(7)]))


class ReportCardTests(GradeTestData):
    def test_rows_per_series_subject_with_grades(self):
        for bimester, score in enumerate(["3", "4", "5", "6"], start=1):
            self.grade(self.ps, "2", bimester).save()
            self.grade(self.pb, score, bimester).save()

        [row] = report_card(self.enrollment)

        self.assertEqual(row.subject, self.math)
        self.assertEqual(
            row.bimesters,
            [Decimal("5.00"), Decimal("6.00"), Decimal("7.00"), Decimal("8.00")],
        )
        self.assertEqual(row.final, Decimal("6.50"))
        self.assertTrue(row.passed)

    def test_final_is_empty_until_the_year_is_complete(self):
        self.grade(self.pb, "5", 1).save()
        [row] = report_card(self.enrollment)
        self.assertEqual(row.bimesters, [Decimal("5.00"), None, None, None])
        self.assertIsNone(row.final)
        self.assertIsNone(row.passed)


class GradeValidationTests(GradeTestData):
    def test_score_above_exam_maximum_is_rejected(self):
        with self.assertRaises(ValidationError) as error:
            self.grade(self.extra, "3").full_clean()
        self.assertIn("score", error.exception.message_dict)

    def test_subject_must_be_taught_in_the_series(self):
        with self.assertRaises(ValidationError) as error:
            self.grade(self.ps, "2", subject=self.physics).full_clean()
        self.assertIn("subject", error.exception.message_dict)

    def test_one_grade_per_exam_and_bimester(self):
        self.grade(self.ps, "7").save()
        with self.assertRaises(IntegrityError):
            self.grade(self.ps, "8").save()


class ExamTypeViewTests(GradeTestData):
    def test_htmx_search_returns_table_partial(self):
        response = self.client.get(
            reverse("grades:exam_type_list"), {"q": "bimestral"}, HTTP_HX_REQUEST="true"
        )
        self.assertTemplateUsed(response, "exam_types/partials/exam_type_table.html")
        self.assertEqual(list(response.context["exam_types"]), [self.pb])

    def test_create_uppercases_code_and_flashes(self):
        response = self.client.post(
            reverse("grades:exam_type_add"),
            {
                "name": "Simulado",
                "code": "sim",
                "kind": ExamKind.REGULAR,
                "max_score": "10",
                "order": "5",
            },
            follow=True,
        )
        self.assertRedirects(response, reverse("grades:exam_type_list"))
        self.assertTrue(ExamType.objects.filter(code="SIM").exists())
        self.assertContains(response, "Registro cadastrado com sucesso")

    def test_exam_type_with_grades_is_not_deleted(self):
        self.grade(self.ps, "7").save()
        response = self.client.post(
            reverse("grades:exam_type_delete", args=[self.ps.pk]), follow=True
        )
        self.assertTrue(ExamType.objects.filter(pk=self.ps.pk).exists())
        self.assertContains(response, "possui notas")


class GradeLevelSubjectViewTests(GradeTestData):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        role = EmployeeRoleType.objects.create(role="Professor")
        cls.teachers = [
            Employee.objects.create(
                name=name, cpf=cpf, rg=cpf[-7:], issuing_authority="SSP", role=role
            )
            for name, cpf in [
                ("Carlos Melo", "98765432101"),
                ("Dora Reis", "98765432102"),
            ]
        ]
        cls.outsider = Employee.objects.create(
            name="Eva Prado",
            cpf="98765432103",
            rg="5432103",
            issuing_authority="SSP",
            role=role,
        )
        department = Department.objects.create(name="Exatas")
        department.teachers.set(cls.teachers)
        cls.math.department = department
        cls.math.save()

    def test_filter_by_series_returns_table_partial(self):
        response = self.client.get(
            reverse("grades:grade_level_subject_list"),
            {"grade_level": 1},
            HTTP_HX_REQUEST="true",
        )
        self.assertTemplateUsed(
            response, "grade_level_subjects/partials/grade_level_subject_table.html"
        )
        self.assertEqual(
            list(response.context["grade_level_subjects"]), [self.math_level_1]
        )

    def test_search_by_teacher_lists_each_subject_once(self):
        self.math_level_1.teachers.set(self.teachers)
        response = self.client.get(
            reverse("grades:grade_level_subject_list"), {"q": "e"}
        )
        self.assertEqual(
            list(response.context["grade_level_subjects"]), [self.math_level_1]
        )

    def test_add_with_several_teachers(self):
        url = f"{reverse('grades:grade_level_subject_add')}?grade_level=3"
        response = self.client.get(url)
        self.assertEqual(response.context["form"].initial["grade_level"], 3)
        # The checkbox class must reach each input, not the list's wrapper.
        self.assertTemplateUsed(response, "components/form/checkbox_list.html")
        self.assertNotContains(response, 'id="id_teachers"')

        response = self.client.post(
            url,
            {
                "grade_level": 3,
                "subject": self.math.pk,
                "teachers": [teacher.pk for teacher in self.teachers],
            },
            follow=True,
        )
        self.assertRedirects(response, reverse("grades:grade_level_subject_list"))
        self.assertContains(response, "Registro cadastrado com sucesso")
        level_subject = GradeLevelSubject.objects.get(grade_level=3, subject=self.math)
        self.assertCountEqual(level_subject.teachers.all(), self.teachers)

    def test_weekly_classes_accepts_fractions(self):
        response = self.client.post(
            reverse("grades:grade_level_subject_add"),
            {"grade_level": 3, "subject": self.math.pk, "weekly_classes": "1.5"},
            follow=True,
        )
        level_subject = GradeLevelSubject.objects.get(grade_level=3, subject=self.math)
        self.assertEqual(level_subject.weekly_classes, Decimal("1.5"))
        self.assertContains(response, "1,50")

    def test_weekly_classes_cannot_be_negative(self):
        response = self.client.post(
            reverse("grades:grade_level_subject_add"),
            {"grade_level": 3, "subject": self.math.pk, "weekly_classes": "-1"},
        )
        self.assertIn("weekly_classes", response.context["form"].errors)

    def test_duplicate_subject_shows_friendly_error(self):
        response = self.client.post(
            reverse("grades:grade_level_subject_add"),
            {"grade_level": 1, "subject": self.math.pk},
        )
        self.assertFormError(
            response.context["form"],
            "subject",
            "Esta matéria já está cadastrada nesta série.",
        )

    def test_class_page_lists_the_series_subjects_and_teachers(self):
        self.math_level_1.teachers.set(self.teachers)
        response = self.client.get(
            reverse("classes:class_detail"),
            {
                "school_year": self.school_class.year_id,
                "school_class": self.school_class.pk,
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(list(response.context["level_subjects"]), [self.math_level_1])
        self.assertContains(response, "Carlos Melo, Dora Reis")
        self.assertNotContains(response, "Física")

    def teachers_field(self, **params):
        return self.client.get(
            reverse("grades:grade_level_subject_teachers"),
            params,
            HTTP_HX_REQUEST="true",
        )

    def test_teachers_endpoint_lists_the_subject_department_and_keeps_ticks(self):
        carlos = self.teachers[0]
        response = self.teachers_field(
            subject=self.math.pk, teachers=[carlos.pk, self.outsider.pk]
        )
        self.assertTemplateUsed(
            response, "grade_level_subjects/partials/teachers_field.html"
        )
        field = response.context["form"]["teachers"]
        self.assertCountEqual(field.field.queryset, self.teachers)
        self.assertEqual(
            [choice.data["selected"] for choice in field.subwidgets], [True, False]
        )
        self.assertNotContains(response, "Eva Prado")

    def test_teachers_endpoint_explains_subject_without_department(self):
        response = self.teachers_field(subject=self.physics.pk)
        self.assertEqual(list(response.context["form"]["teachers"].field.queryset), [])
        self.assertContains(response, "não está vinculada a um departamento")

    def test_subject_select_reloads_the_teachers(self):
        response = self.client.get(reverse("grades:grade_level_subject_add"))
        self.assertContains(
            response, f'hx-get="{reverse("grades:grade_level_subject_teachers")}"'
        )

    def test_teacher_outside_the_department_is_rejected(self):
        response = self.client.post(
            reverse("grades:grade_level_subject_add"),
            {"grade_level": 3, "subject": self.math.pk, "teachers": [self.outsider.pk]},
        )
        self.assertIn("teachers", response.context["form"].errors)
        self.assertFalse(GradeLevelSubject.objects.filter(grade_level=3).exists())


class GradeEntryViewTests(GradeTestData):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        dropped = Student.objects.create(
            name="Bruno Lima", cpf="12345678902", rg="5678902", issuing_authority="SSP"
        )
        Enrollment.objects.create(
            student=dropped,
            enrollment_type=cls.enrollment.enrollment_type,
            school_class=cls.school_class,
            status=EnrollmentStatus.DROPPED,
            enrolled_at=date(2027, 1, 15),
            due_day=10,
        )

    def params(self, **overrides):
        return {
            "school_year": self.school_class.year_id,
            "school_class": self.school_class.pk,
            "subject": self.math.pk,
            "bimester": 1,
            **overrides,
        }

    def url(self, **overrides):
        query = "&".join(f"{k}={v}" for k, v in self.params(**overrides).items())
        return f"{reverse('grades:grade_entry')}?{query}"

    def field(self, exam_type):
        return f"score_{self.enrollment.pk}_{exam_type.pk}"

    def test_sheet_has_a_row_per_active_enrollment(self):
        response = self.client.get(self.url(), HTTP_HX_REQUEST="true")
        self.assertTemplateUsed(response, "grade_entry/partials/grade_sheet.html")
        form = response.context["form"]
        self.assertEqual(form.enrollments, [self.enrollment])
        self.assertIn(self.field(self.pb), form.fields)

    def test_no_sheet_until_bimester_is_chosen(self):
        params = self.params()
        del params["bimester"]
        response = self.client.get(reverse("grades:grade_entry"), params)
        self.assertIsNone(response.context["form"])

    def test_options_drop_class_of_another_year_and_push_url(self):
        other_year = SchoolYear.objects.create(
            begins=date(2028, 1, 10), ends=date(2028, 12, 15)
        )
        response = self.client.get(
            reverse("grades:grade_entry_options"),
            {"school_year": other_year.pk, "school_class": self.school_class.pk},
            HTTP_HX_REQUEST="true",
        )
        self.assertTemplateUsed(response, "grade_entry/partials/grade_selects.html")
        self.assertIsNone(response.context["selected_class_id"])
        self.assertContains(response, 'hx-swap-oob="true"')
        self.assertEqual(
            response["HX-Push-Url"],
            f"{reverse('grades:grade_entry')}?school_year={other_year.pk}",
        )

    def test_options_list_subjects_of_the_class(self):
        response = self.client.get(
            reverse("grades:grade_entry_options"),
            {
                "school_year": self.school_class.year_id,
                "school_class": self.school_class.pk,
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(
            [item.subject for item in response.context["level_subjects"]], [self.math]
        )

    def test_post_creates_updates_and_deletes_grades(self):
        self.grade(self.ps, "5").save()
        self.grade(self.extra, "1").save()
        response = self.client.post(
            self.url(),
            {
                self.field(self.ps): "2,5",
                self.field(self.pb): "5,5",
                self.field(self.behavior): "",
                self.field(self.extra): "",
                self.field(self.recovery): "",
            },
        )
        self.assertRedirects(response, self.url())
        scores = dict(
            Grade.objects.filter(enrollment=self.enrollment).values_list(
                "exam_type__code", "score"
            )
        )
        self.assertEqual(scores, {"PS": Decimal("2.50"), "PB": Decimal("5.50")})

    def test_invalid_score_saves_nothing(self):
        response = self.client.post(
            self.url(),
            # PS above its maximum of 3.
            {self.field(self.ps): "4", self.field(self.pb): "5"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(Grade.objects.exists())

    def test_subject_of_another_series_shows_no_sheet(self):
        response = self.client.get(self.url(subject=self.physics.pk))
        self.assertIsNone(response.context["form"])


class ReportCardViewTests(GradeTestData):
    def test_shows_a_row_per_series_subject(self):
        self.grade(self.pb, "5").save()
        response = self.client.get(
            reverse("grades:report_card", args=[self.enrollment.pk])
        )
        self.assertTemplateUsed(response, "report_cards/report_card.html")
        [row] = response.context["rows"]
        self.assertEqual(row.bimesters[0], Decimal("5.00"))
        self.assertContains(response, "Em andamento")

    def test_enrollment_list_links_to_the_report_card(self):
        response = self.client.get(reverse("enrollments:enrollment_list"))
        self.assertContains(
            response, reverse("grades:report_card", args=[self.enrollment.pk])
        )
