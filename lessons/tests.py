from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.urls import reverse

from base.testing import LoggedInTestCase
from classes.models import Class, Shift
from departments.models import Department
from employees.models import Employee, EmployeeRoleType
from grades.models import GradeLevelSubject, Subject
from incidents.tests import create_enrollment
from lessons.models import Lecture, TimetableSlot, Weekday

HTMX = {"HTTP_HX_REQUEST": "true"}
MONDAY = date(2027, 3, 1)
SATURDAY = date(2027, 3, 6)
SUNDAY = date(2027, 3, 7)


class LessonFixturesMixin:
    @classmethod
    def setUpTestData(cls):
        cls.school_class = create_enrollment().school_class
        cls.school_class.shift = Shift.MORNING
        cls.school_class.save()
        cls.other_class = Class.objects.create(
            program=cls.school_class.program,
            year=cls.school_class.year,
            name="B",
            grade_level=1,
            shift=Shift.MORNING,
        )
        role = EmployeeRoleType.objects.create(role="Professor")
        cls.teacher, cls.substitute, cls.outsider = [
            Employee.objects.create(
                name=name, cpf=cpf, rg=cpf[-7:], issuing_authority="SSP", role=role
            )
            for name, cpf in [
                ("Carlos Melo", "98765432101"),
                ("Dora Reis", "98765432102"),
                ("Eva Prado", "98765432103"),
            ]
        ]
        department = Department.objects.create(name="Exatas")
        department.teachers.set([cls.teacher, cls.substitute])
        cls.math = GradeLevelSubject.objects.create(
            grade_level=1,
            subject=Subject.objects.create(name="Matemática", department=department),
            weekly_classes=Decimal(2),
        )
        cls.math.teachers.set([cls.teacher])
        cls.physics_2 = GradeLevelSubject.objects.create(
            grade_level=2,
            subject=Subject.objects.create(name="Física", department=department),
        )
        cls.physics_2.teachers.set([cls.teacher])

    def slot(self, school_class=None, weekday=Weekday.MONDAY, period=1, **kwargs):
        return TimetableSlot(
            school_class=school_class or self.school_class,
            weekday=weekday,
            period=period,
            subject=kwargs.get("subject", self.math),
            teacher=kwargs.get("teacher", self.teacher),
        )

    def lecture(self, day=MONDAY, period=1, **kwargs):
        return Lecture(
            school_class=self.school_class,
            date=day,
            period=period,
            subject=kwargs.get("subject", self.math),
            teacher=kwargs.get("teacher", self.teacher),
            topic=kwargs.get("topic", "Funções"),
        )


class TimetableSlotModelTests(LessonFixturesMixin, LoggedInTestCase):
    def test_subject_must_be_in_the_class_series(self):
        with self.assertRaisesMessage(ValidationError, "não é oferecida na série"):
            self.slot(subject=self.physics_2).full_clean()

    def test_teacher_must_teach_the_subject(self):
        with self.assertRaisesMessage(ValidationError, "não leciona esta matéria"):
            self.slot(teacher=self.substitute).full_clean()

    def test_teacher_cannot_be_in_two_classes_at_once(self):
        self.slot(school_class=self.other_class).save()
        with self.assertRaisesMessage(ValidationError, "já tem aula na turma"):
            self.slot().full_clean()

    def test_weekdays_have_twelve_periods_and_saturday_seven(self):
        self.slot(weekday=Weekday.FRIDAY, period=12).full_clean()
        self.slot(weekday=Weekday.SATURDAY, period=7).full_clean()
        with self.assertRaisesMessage(ValidationError, "sábado tem só 7 aulas"):
            self.slot(weekday=Weekday.SATURDAY, period=8).full_clean()

    def test_same_period_in_another_shift_is_not_a_clash(self):
        self.other_class.shift = Shift.AFTERNOON
        self.other_class.save()
        self.slot(school_class=self.other_class).save()
        self.slot().full_clean()


class LectureModelTests(LessonFixturesMixin, LoggedInTestCase):
    def test_lectures_are_from_monday_to_saturday(self):
        self.lecture(day=SATURDAY).full_clean()
        with self.assertRaisesMessage(ValidationError, "segunda a sábado"):
            self.lecture(day=SUNDAY).full_clean()

    def test_saturday_lectures_stop_at_the_seventh_period(self):
        self.lecture(period=12).full_clean()
        with self.assertRaisesMessage(ValidationError, "sábado tem só 7 aulas"):
            self.lecture(day=SATURDAY, period=8).full_clean()

    def test_lectures_are_inside_the_school_year(self):
        with self.assertRaisesMessage(ValidationError, "fora do ano escolar"):
            self.lecture(day=date(2028, 3, 1)).full_clean()

    def test_substitute_from_the_department_is_accepted(self):
        self.lecture(teacher=self.substitute).full_clean()

    def test_teacher_outside_the_department_is_rejected(self):
        with self.assertRaisesMessage(ValidationError, "não é do departamento"):
            self.lecture(teacher=self.outsider).full_clean()

    def test_subject_in_use_cannot_be_deleted(self):
        self.lecture().save()
        with self.assertRaises(ProtectedError):
            self.math.delete()


class TimetableViewsTests(LessonFixturesMixin, LoggedInTestCase):
    def test_grid_and_weekly_load_warning(self):
        self.slot().save()
        response = self.client.get(
            reverse("lessons:timetable"),
            {"school_class": self.school_class.pk},
            **HTMX,
        )
        self.assertTemplateUsed(response, "timetable/partials/timetable_grid.html")
        self.assertContains(response, "Carlos Melo")
        # 1 period scheduled, 2 expected.
        self.assertContains(response, "Diferente do previsto")

    def test_edit_saves_and_clears_cells(self):
        old = self.slot(weekday=Weekday.FRIDAY, period=7)
        old.save()
        value = f"{self.math.pk}-{self.teacher.pk}"
        response = self.client.post(
            reverse("lessons:timetable_edit", args=[self.school_class.pk]),
            {"slot_1_1": value, "slot_2_3": value},
        )
        self.assertRedirects(
            response,
            f"{reverse('lessons:timetable')}?school_class={self.school_class.pk}",
        )
        self.assertEqual(
            set(self.school_class.timetable_slots.values_list("weekday", "period")),
            {(1, 1), (2, 3)},
        )

    def test_edit_has_twelve_periods_and_seven_on_saturday(self):
        response = self.client.get(
            reverse("lessons:timetable_edit", args=[self.school_class.pk])
        )
        form = response.context["form"]
        self.assertIn("slot_5_12", form.fields)
        self.assertIn("slot_6_7", form.fields)
        self.assertNotIn("slot_6_8", form.fields)
        self.assertContains(response, "Sábado")

    def test_clash_saves_nothing(self):
        self.slot(school_class=self.other_class).save()
        value = f"{self.math.pk}-{self.teacher.pk}"
        response = self.client.post(
            reverse("lessons:timetable_edit", args=[self.school_class.pk]),
            {"slot_1_1": value, "slot_1_2": value},
        )
        self.assertContains(response, "já tem aula na turma")
        self.assertFalse(self.school_class.timetable_slots.exists())


class LectureDayViewTests(LessonFixturesMixin, LoggedInTestCase):
    def url(self, day=MONDAY):
        return (
            f"{reverse('lessons:lecture_day')}"
            f"?school_class={self.school_class.pk}&date={day:%Y-%m-%d}"
        )

    def test_sheet_is_prefilled_from_the_timetable(self):
        self.slot(period=2).save()
        response = self.client.get(self.url(), **HTMX)
        self.assertTemplateUsed(response, "lectures/partials/lecture_day_sheet.html")
        form = response.context["form"]
        self.assertEqual(form["subject_2"].initial, self.math.pk)
        self.assertEqual(form["teacher_2"].initial, self.teacher.pk)
        self.assertIsNone(form["subject_1"].initial)

    def test_saves_rows_with_topic_and_deletes_cleared_ones(self):
        self.lecture(period=3).save()
        response = self.client.post(
            self.url(),
            {
                "subject_1": self.math.pk,
                "teacher_1": self.substitute.pk,
                "topic_1": "Funções do 2º grau",
                # Planned but without a topic: not saved.
                "subject_2": self.math.pk,
                "teacher_2": self.teacher.pk,
                "topic_2": "",
                # Saved before, topic cleared: deleted.
                "subject_3": self.math.pk,
                "teacher_3": self.teacher.pk,
                "topic_3": "",
            },
        )
        self.assertRedirects(response, self.url())
        lecture = Lecture.objects.get()
        self.assertEqual(
            (lecture.period, lecture.teacher, lecture.topic),
            (1, self.substitute, "Funções do 2º grau"),
        )

    def test_invalid_row_saves_nothing(self):
        response = self.client.post(
            self.url(),
            {
                "subject_1": self.math.pk,
                "teacher_1": self.teacher.pk,
                "topic_1": "Funções",
                "subject_2": self.math.pk,
                "topic_2": "Gráficos",
            },
        )
        self.assertContains(response, "Informe o professor.")
        self.assertFalse(Lecture.objects.exists())

    def test_saturday_sheet_has_seven_rows(self):
        self.assertEqual(
            len(list(self.client.get(self.url(), **HTMX).context["form"].rows())), 12
        )
        form = self.client.get(self.url(SATURDAY), **HTMX).context["form"]
        self.assertEqual(len(list(form.rows())), 7)

    def test_sunday_shows_an_error_instead_of_the_sheet(self):
        response = self.client.get(self.url(SUNDAY), **HTMX)
        self.assertIsNone(response.context["form"])
        self.assertContains(response, "segunda a sábado")


class LectureCrudViewsTests(LessonFixturesMixin, LoggedInTestCase):
    def test_list_filter_edit_and_delete(self):
        lecture = self.lecture()
        lecture.save()
        self.lecture(period=2, teacher=self.substitute, topic="Gráficos").save()

        response = self.client.get(
            reverse("lessons:lecture_list"), {"teacher": self.substitute.pk}, **HTMX
        )
        self.assertTemplateUsed(response, "lectures/partials/lecture_table.html")
        self.assertEqual(
            [item.topic for item in response.context["lectures"]], ["Gráficos"]
        )

        response = self.client.post(
            reverse("lessons:lecture_edit", args=[lecture.pk]),
            {
                "date": "2027-03-01",
                "period": 1,
                "subject": self.math.pk,
                "teacher": self.teacher.pk,
                "topic": "Funções afins",
            },
        )
        self.assertRedirects(response, reverse("lessons:lecture_list"))
        lecture.refresh_from_db()
        self.assertEqual(lecture.topic, "Funções afins")

        response = self.client.post(
            reverse("lessons:lecture_edit", args=[lecture.pk]),
            {
                "date": "2027-03-01",
                "period": 2,
                "subject": self.math.pk,
                "teacher": self.teacher.pk,
                "topic": "Funções afins",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())

        response = self.client.post(
            reverse("lessons:lecture_delete", args=[lecture.pk])
        )
        self.assertRedirects(response, reverse("lessons:lecture_list"))
        self.assertFalse(Lecture.objects.filter(pk=lecture.pk).exists())


class LessonPagesTests(LessonFixturesMixin, LoggedInTestCase):
    def test_full_pages_render(self):
        self.slot().save()
        lecture = self.lecture()
        lecture.save()
        class_query = f"?school_class={self.school_class.pk}"
        for url in [
            reverse("lessons:timetable"),
            reverse("lessons:timetable") + class_query,
            reverse("lessons:timetable_edit", args=[self.school_class.pk]),
            reverse("lessons:lecture_list"),
            reverse("lessons:lecture_day") + class_query + "&date=2027-03-01",
            reverse("lessons:lecture_edit", args=[lecture.pk]),
            reverse("lessons:lecture_delete", args=[lecture.pk]),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
