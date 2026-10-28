from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.urls import reverse

from base.testing import LoggedInTestCase
from enrollments.models import Enrollment, EnrollmentType, SchoolYear
from grades.models import ExamKind, ExamType, Grade, GradeLevelSubject, Subject
from incidents.tests import create_enrollment
from pathways.models import (
    AttendanceStatus,
    ExtraGradeSettings,
    Pathway,
    PathwayAttendance,
    PathwayEnrollment,
    PathwayGrade,
    PathwayOffering,
    PathwaySession,
)
from pathways.services import extra_grades, save_extra_grades
from q_and_a.models import QandA
from students.models import Student

HTMX = {"HTTP_HX_REQUEST": "true"}


class PathwayFixturesMixin:
    @classmethod
    def setUpTestData(cls):
        cls.enrollment = create_enrollment()
        cls.school_year = cls.enrollment.enrollment_type.school_year
        cls.school_year.bi_1_begins = date(2027, 2, 1)
        cls.school_year.bi_1_ends = date(2027, 4, 15)
        cls.school_year.save()
        cls.other = Enrollment.objects.create(
            student=Student.objects.create(
                name="Bruno Lima",
                cpf="12345678902",
                rg="7654321",
                issuing_authority="SSP",
            ),
            enrollment_type=cls.enrollment.enrollment_type,
            school_class=cls.enrollment.school_class,
        )
        cls.robotics = Pathway.objects.create(
            name="Robótica", extra_points=Decimal("0.5")
        )
        cls.theater = Pathway.objects.create(name="Teatro", extra_points=Decimal(1))
        cls.offering = PathwayOffering.objects.create(
            pathway=cls.robotics, school_year=cls.school_year
        )
        cls.member = PathwayEnrollment.objects.create(
            enrollment=cls.enrollment,
            offering=cls.offering,
            joined_at=date(2027, 2, 1),
        )


class PathwayModelTests(PathwayFixturesMixin, LoggedInTestCase):
    def test_offering_must_be_in_the_enrollment_school_year(self):
        other_year = SchoolYear.objects.create(
            begins=date(2028, 1, 10), ends=date(2028, 12, 15)
        )
        offering = PathwayOffering.objects.create(
            pathway=self.theater, school_year=other_year
        )
        member = PathwayEnrollment(
            enrollment=self.enrollment, offering=offering, joined_at=date(2027, 2, 1)
        )
        with self.assertRaisesMessage(ValidationError, "outro ano escolar"):
            member.full_clean()

    def test_capacity_counts_only_current_members(self):
        self.offering.capacity = 1
        self.offering.save()
        member = PathwayEnrollment(
            enrollment=self.other, offering=self.offering, joined_at=date(2027, 2, 1)
        )
        with self.assertRaisesMessage(ValidationError, "Não há vagas"):
            member.full_clean()

        self.member.left_at = date(2027, 3, 1)
        self.member.save()
        member.full_clean()

    def test_left_before_joined_is_invalid(self):
        self.member.left_at = date(2027, 1, 20)
        with self.assertRaisesMessage(ValidationError, "antes da entrada"):
            self.member.full_clean()

    def test_attendance_only_while_a_member(self):
        self.member.left_at = date(2027, 3, 1)
        self.member.save()
        session = PathwaySession.objects.create(
            offering=self.offering, date=date(2027, 3, 10)
        )
        attendance = PathwayAttendance(session=session, pathway_enrollment=self.member)
        with self.assertRaisesMessage(ValidationError, "não estava inscrito"):
            attendance.full_clean()

    def test_session_inside_the_school_year(self):
        session = PathwaySession(offering=self.offering, date=date(2028, 2, 1))
        with self.assertRaisesMessage(ValidationError, "fora do ano escolar"):
            session.full_clean()

    def test_grade_up_to_the_pathway_maximum(self):
        grade = PathwayGrade(
            pathway_enrollment=self.member, bimester=1, score=Decimal("0.6")
        )
        with self.assertRaisesMessage(ValidationError, "nota máxima"):
            grade.full_clean()

        grade.score = Decimal("0.5")
        grade.full_clean()

    def test_pathway_without_extra_grade_takes_no_grade(self):
        self.robotics.extra_points = 0
        self.robotics.save()
        grade = PathwayGrade(pathway_enrollment=self.member, bimester=1, score=0)
        with self.assertRaisesMessage(ValidationError, "não dá nota extra"):
            grade.full_clean()

    def test_settings_created_with_defaults(self):
        settings = ExtraGradeSettings.for_school_year(self.school_year)
        self.assertEqual(settings.q_and_a_min_sessions, 3)
        self.assertEqual(settings.q_and_a_points, Decimal("0.5"))
        self.assertEqual(ExtraGradeSettings.for_school_year(self.school_year), settings)


class ExtraGradeTests(PathwayFixturesMixin, LoggedInTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.extra = ExamType.objects.create(
            name="Nota extra", code="EX", kind=ExamKind.BONUS, max_score=Decimal(1)
        )
        cls.math = Subject.objects.create(name="Matemática")
        cls.history = Subject.objects.create(name="História")
        GradeLevelSubject.objects.create(grade_level=1, subject=cls.math)
        GradeLevelSubject.objects.create(grade_level=1, subject=cls.history)

    def lessons(self, member, statuses, start_day=1):
        for day, status in enumerate(statuses, start=start_day):
            session = PathwaySession.objects.create(
                offering=member.offering, date=date(2027, 3, day)
            )
            PathwayAttendance.objects.create(
                session=session, pathway_enrollment=member, status=status
            )

    def grade(self, member, score, bimester=1):
        PathwayGrade.objects.create(
            pathway_enrollment=member, bimester=bimester, score=Decimal(score)
        )

    def q_and_as(self, count, day=None):
        for _ in range(count):
            QandA.objects.create(
                enrollment=self.enrollment,
                subject=self.math,
                q_and_a_date=day or date(2027, 3, 1),
            )

    def extra_of(self, enrollment, bimester=1):
        return extra_grades([enrollment], bimester, self.extra).get(enrollment.pk)

    def test_pathway_grade_is_added_as_given(self):
        F = AttendanceStatus.ABSENT
        self.lessons(self.member, [AttendanceStatus.PRESENT, F, F, F])
        self.grade(self.member, "0.4")
        # Attendance doesn't change the teacher's grade.
        self.assertEqual(self.extra_of(self.enrollment), Decimal("0.40"))

    def test_no_grade_gives_nothing(self):
        self.lessons(self.member, [AttendanceStatus.PRESENT])
        self.assertEqual(self.extra_of(self.enrollment), 0)

    def test_grades_of_other_bimesters_dont_count(self):
        self.grade(self.member, "0.5", bimester=2)
        self.assertEqual(self.extra_of(self.enrollment), 0)

    def test_pathway_without_extra_grade_counts_zero(self):
        self.grade(self.member, "0.5")
        self.robotics.extra_points = 0
        self.robotics.save()
        self.assertEqual(self.extra_of(self.enrollment), 0)

    def test_q_and_a_points_from_the_minimum_sessions(self):
        self.q_and_as(2)
        self.q_and_as(1, day=date(2027, 5, 1))  # outside the bimester
        self.assertEqual(self.extra_of(self.enrollment), 0)

        self.q_and_as(1)
        self.assertEqual(self.extra_of(self.enrollment), Decimal("0.5"))

        settings = ExtraGradeSettings.for_school_year(self.school_year)
        settings.q_and_a_min_sessions = 4
        settings.q_and_a_points = Decimal("0.3")
        settings.save()
        self.q_and_as(1)
        self.assertEqual(self.extra_of(self.enrollment), Decimal("0.3"))

    def test_sources_add_up_to_the_exam_maximum(self):
        theater = PathwayEnrollment.objects.create(
            enrollment=self.enrollment,
            offering=PathwayOffering.objects.create(
                pathway=self.theater, school_year=self.school_year
            ),
            joined_at=date(2027, 2, 1),
        )
        self.grade(self.member, "0.3")
        self.grade(theater, "0.5")
        self.assertEqual(self.extra_of(self.enrollment), Decimal("0.80"))

        self.q_and_as(3)  # 0.50, capped at the exam's 1.00
        self.assertEqual(self.extra_of(self.enrollment), Decimal(1))

    def test_bimester_without_dates_is_skipped(self):
        self.assertEqual(extra_grades([self.enrollment], 2, self.extra), {})

    def test_save_writes_every_subject_zero_included(self):
        self.grade(self.member, "0.5")
        Grade.objects.create(
            enrollment=self.other,
            subject=self.math,
            exam_type=self.extra,
            bimester=1,
            score=Decimal(1),
        )

        graded = save_extra_grades([self.enrollment, self.other], 1, self.extra)

        self.assertEqual(graded, 2)
        scores = dict(
            Grade.objects.filter(
                enrollment=self.enrollment, exam_type=self.extra, bimester=1
            ).values_list("subject__name", "score")
        )
        self.assertEqual(
            scores, {"Matemática": Decimal("0.5"), "História": Decimal("0.5")}
        )
        self.assertEqual(
            sorted(
                Grade.objects.filter(
                    enrollment=self.other, exam_type=self.extra
                ).values_list("score", flat=True)
            ),
            [0, 0],
        )


class ExtraGradeSettingsViewsTests(LoggedInTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school_year = SchoolYear.objects.create(
            begins=date(2027, 1, 10), ends=date(2027, 12, 15)
        )

    def test_list_shows_defaults_before_first_edit(self):
        url = reverse("pathways:extra_grade_settings_list")
        response = self.client.get(url)
        self.assertTemplateUsed(
            response, "extra_grade_settings/extra_grade_settings_list.html"
        )
        self.assertContains(response, "0,50")
        self.assertFalse(ExtraGradeSettings.objects.exists())

        response = self.client.get(url, {"q": "2027"}, **HTMX)
        self.assertTemplateUsed(
            response, "extra_grade_settings/partials/extra_grade_settings_table.html"
        )
        self.assertContains(response, "2027")

    def test_edit(self):
        url = reverse("pathways:extra_grade_settings_edit", args=[self.school_year.pk])
        self.assertEqual(self.client.get(url).status_code, 200)

        response = self.client.post(
            url,
            {"q_and_a_min_sessions": "2", "q_and_a_points": "0.25"},
        )
        self.assertRedirects(response, reverse("pathways:extra_grade_settings_list"))
        settings = ExtraGradeSettings.objects.get(school_year=self.school_year)
        self.assertEqual(settings.q_and_a_min_sessions, 2)
        self.assertEqual(settings.q_and_a_points, Decimal("0.25"))

    def test_negative_points_are_rejected(self):
        url = reverse("pathways:extra_grade_settings_edit", args=[self.school_year.pk])
        response = self.client.post(
            url, {"q_and_a_min_sessions": "2", "q_and_a_points": "-1"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            ExtraGradeSettings.objects.get().q_and_a_points, Decimal("0.5")
        )


class PathwayViewsTests(LoggedInTestCase):
    def test_crud(self):
        response = self.client.post(
            reverse("pathways:pathway_add"),
            {"name": "Robótica", "extra_points": "0.5", "description": ""},
        )
        self.assertRedirects(response, reverse("pathways:pathway_list"))
        pathway = Pathway.objects.get()

        response = self.client.post(
            reverse("pathways:pathway_edit", args=[pathway.pk]),
            {"name": "Robótica avançada", "extra_points": "1", "description": ""},
        )
        self.assertRedirects(response, reverse("pathways:pathway_list"))
        pathway.refresh_from_db()
        self.assertEqual(pathway.extra_points, Decimal(1))

        response = self.client.get(
            reverse("pathways:pathway_list"), {"q": "avançada"}, **HTMX
        )
        self.assertTemplateUsed(response, "pathways/partials/pathway_table.html")
        self.assertContains(response, "Robótica avançada")

        self.client.post(reverse("pathways:pathway_delete", args=[pathway.pk]))
        self.assertFalse(Pathway.objects.exists())

    def test_list_page_renders(self):
        response = self.client.get(reverse("pathways:pathway_list"))
        self.assertTemplateUsed(response, "pathways/pathway_list.html")


class PathwayOfferingViewsTests(PathwayFixturesMixin, LoggedInTestCase):
    def test_crud(self):
        data = {
            "pathway": self.theater.pk,
            "school_year": self.school_year.pk,
            "name": "Manhã",
            "schedule": "Terças, 14h",
            "capacity": "20",
        }
        response = self.client.post(reverse("pathways:pathway_offering_add"), data)
        self.assertRedirects(response, reverse("pathways:pathway_offering_list"))
        offering = PathwayOffering.objects.get(pathway=self.theater)

        response = self.client.post(
            reverse("pathways:pathway_offering_edit", args=[offering.pk]),
            {**data, "name": "Tarde"},
        )
        self.assertRedirects(response, reverse("pathways:pathway_offering_list"))
        offering.refresh_from_db()
        self.assertEqual(offering.name, "Tarde")

        self.client.post(
            reverse("pathways:pathway_offering_delete", args=[offering.pk])
        )
        self.assertFalse(PathwayOffering.objects.filter(pk=offering.pk).exists())

    def test_duplicate_offering_is_rejected(self):
        response = self.client.post(
            reverse("pathways:pathway_offering_add"),
            {"pathway": self.robotics.pk, "school_year": self.school_year.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PathwayOffering.objects.count(), 1)

    def test_list_filters_and_counts_current_members(self):
        PathwayEnrollment.objects.create(
            enrollment=self.other,
            offering=self.offering,
            joined_at=date(2027, 2, 1),
            left_at=date(2027, 3, 1),
        )
        response = self.client.get(
            reverse("pathways:pathway_offering_list"),
            {"pathway": self.robotics.pk},
            **HTMX,
        )
        self.assertTemplateUsed(
            response, "pathway_offerings/partials/pathway_offering_table.html"
        )
        self.assertEqual(list(response.context["offerings"]), [self.offering])
        self.assertEqual(response.context["offerings"][0].members, 1)

    def test_delete_blocked_with_members(self):
        response = self.client.post(
            reverse("pathways:pathway_offering_delete", args=[self.offering.pk])
        )
        self.assertRedirects(response, reverse("pathways:pathway_offering_list"))
        self.assertTrue(PathwayOffering.objects.filter(pk=self.offering.pk).exists())


class PathwayEnrollmentViewsTests(PathwayFixturesMixin, LoggedInTestCase):
    def roster_url(self):
        return (
            f"{reverse('pathways:pathway_enrollment_list')}?offering={self.offering.pk}"
        )

    def test_add_from_the_offering(self):
        other_year = Enrollment.objects.create(
            student=Student.objects.create(
                name="Caio Reis", cpf="12345678903", rg="111", issuing_authority="SSP"
            ),
            enrollment_type=EnrollmentType.objects.create(
                program=self.enrollment.enrollment_type.program,
                school_year=SchoolYear.objects.create(
                    begins=date(2028, 1, 10), ends=date(2028, 12, 15)
                ),
                total_price=Decimal("1000.00"),
            ),
        )
        url = reverse("pathways:pathway_enrollment_add")
        response = self.client.get(url, {"offering": self.offering.pk})
        form = response.context["form"]
        self.assertEqual(form.initial["offering"], self.offering.pk)
        self.assertIn(self.other, form.fields["enrollment"].queryset)
        self.assertNotIn(other_year, form.fields["enrollment"].queryset)

        response = self.client.post(
            url,
            {
                "offering": self.offering.pk,
                "enrollment": self.other.pk,
                "joined_at": "2027-02-10",
            },
        )
        self.assertRedirects(response, self.roster_url())
        self.assertTrue(
            PathwayEnrollment.objects.filter(
                enrollment=self.other, offering=self.offering
            ).exists()
        )

    def test_full_offering_is_rejected(self):
        self.offering.capacity = 1
        self.offering.save()
        response = self.client.post(
            reverse("pathways:pathway_enrollment_add"),
            {
                "offering": self.offering.pk,
                "enrollment": self.other.pk,
                "joined_at": "2027-02-10",
            },
        )
        self.assertContains(response, "Não há vagas")

    def test_leaving_and_status_filter(self):
        response = self.client.post(
            reverse("pathways:pathway_enrollment_edit", args=[self.member.pk]),
            {
                "offering": self.offering.pk,
                "enrollment": self.enrollment.pk,
                "joined_at": "2027-02-01",
                "left_at": "2027-05-01",
            },
        )
        self.assertRedirects(response, self.roster_url())

        url = reverse("pathways:pathway_enrollment_list")
        response = self.client.get(url, {"status": "current"}, **HTMX)
        self.assertTemplateUsed(
            response, "pathway_enrollments/partials/pathway_enrollment_table.html"
        )
        self.assertEqual(list(response.context["pathway_enrollments"]), [])
        response = self.client.get(url, {"status": "left"}, **HTMX)
        self.assertEqual(list(response.context["pathway_enrollments"]), [self.member])

    def test_delete_blocked_with_attendance(self):
        session = PathwaySession.objects.create(
            offering=self.offering, date=date(2027, 3, 1)
        )
        PathwayAttendance.objects.create(
            session=session, pathway_enrollment=self.member
        )
        response = self.client.post(
            reverse("pathways:pathway_enrollment_delete", args=[self.member.pk])
        )
        self.assertRedirects(response, self.roster_url())
        self.assertTrue(PathwayEnrollment.objects.filter(pk=self.member.pk).exists())


class PathwaySessionViewsTests(PathwayFixturesMixin, LoggedInTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.left = PathwayEnrollment.objects.create(
            enrollment=cls.other,
            offering=cls.offering,
            joined_at=date(2027, 2, 1),
            left_at=date(2027, 3, 5),
        )

    def test_create_then_take_the_roll_call(self):
        response = self.client.post(
            reverse("pathways:pathway_session_add"),
            {"offering": self.offering.pk, "date": "2027-03-10", "topic": "Sensores"},
        )
        session = PathwaySession.objects.get()
        url = reverse("pathways:pathway_session_attendance", args=[session.pk])
        self.assertRedirects(response, url)

        response = self.client.get(url)
        self.assertEqual(response.context["form"].members, [self.member])
        self.assertContains(response, "Ana Souza")
        self.assertNotContains(response, "Bruno Lima")

        response = self.client.post(
            url, {f"status_{self.member.pk}": AttendanceStatus.ABSENT}
        )
        list_url = (
            f"{reverse('pathways:pathway_session_list')}?offering={self.offering.pk}"
        )
        self.assertRedirects(response, list_url)
        self.assertEqual(
            PathwayAttendance.objects.get(pathway_enrollment=self.member).status,
            AttendanceStatus.ABSENT,
        )

        response = self.client.get(list_url, **HTMX)
        self.assertTemplateUsed(
            response, "pathway_sessions/partials/pathway_session_table.html"
        )
        listed = response.context["sessions"][0]
        self.assertEqual((listed.present, listed.absent), (0, 1))

    def test_date_outside_the_school_year_is_rejected(self):
        response = self.client.post(
            reverse("pathways:pathway_session_add"),
            {"offering": self.offering.pk, "date": "2028-03-10"},
        )
        self.assertContains(response, "fora do ano escolar")
        self.assertFalse(PathwaySession.objects.exists())

    def test_moving_the_date_drops_students_not_enrolled_then(self):
        session = PathwaySession.objects.create(
            offering=self.offering, date=date(2027, 3, 1)
        )
        for member in (self.member, self.left):
            PathwayAttendance.objects.create(session=session, pathway_enrollment=member)

        response = self.client.post(
            reverse("pathways:pathway_session_edit", args=[session.pk]),
            {"offering": self.theater.pk, "date": "2027-03-10", "topic": ""},
        )
        self.assertRedirects(
            response,
            f"{reverse('pathways:pathway_session_list')}?offering={self.offering.pk}",
        )
        session.refresh_from_db()
        self.assertEqual(session.offering, self.offering)  # can't be changed
        self.assertEqual(
            list(session.attendances.values_list("pathway_enrollment", flat=True)),
            [self.member.pk],
        )

    def test_delete_removes_the_roll_call(self):
        session = PathwaySession.objects.create(
            offering=self.offering, date=date(2027, 3, 1)
        )
        PathwayAttendance.objects.create(
            session=session, pathway_enrollment=self.member
        )
        self.client.post(reverse("pathways:pathway_session_delete", args=[session.pk]))
        self.assertFalse(PathwaySession.objects.exists())
        self.assertFalse(PathwayAttendance.objects.exists())


class PathwayGradeEntryTests(PathwayFixturesMixin, LoggedInTestCase):
    def sheet_url(self, bimester=1):
        return (
            f"{reverse('pathways:pathway_grade_entry')}"
            f"?offering={self.offering.pk}&bimester={bimester}"
        )

    def test_sheet_shows_attendance(self):
        session = PathwaySession.objects.create(
            offering=self.offering, date=date(2027, 3, 1)
        )
        PathwayAttendance.objects.create(
            session=session, pathway_enrollment=self.member
        )
        response = self.client.get(self.sheet_url(), **HTMX)
        self.assertTemplateUsed(
            response, "pathway_grades/partials/pathway_grade_sheet.html"
        )
        [(member, _, rate)] = list(response.context["form"].rows())
        self.assertEqual(member, self.member)
        self.assertEqual(rate, Decimal(100))

    def test_save_updates_and_blank_deletes(self):
        field = f"score_{self.member.pk}"
        response = self.client.post(self.sheet_url(), {field: "0,4"})
        self.assertRedirects(response, self.sheet_url())
        self.assertEqual(PathwayGrade.objects.get().score, Decimal("0.4"))

        self.client.post(self.sheet_url(), {field: ""})
        self.assertFalse(PathwayGrade.objects.exists())

    def test_score_over_the_pathway_maximum_saves_nothing(self):
        response = self.client.post(
            self.sheet_url(), {f"score_{self.member.pk}": "0,6"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(PathwayGrade.objects.exists())

    def test_pathway_without_extra_grade_has_no_sheet(self):
        self.robotics.extra_points = 0
        self.robotics.save()
        response = self.client.get(self.sheet_url(), **HTMX)
        self.assertIsNone(response.context["form"])

    def test_without_selection_shows_no_sheet(self):
        response = self.client.get(reverse("pathways:pathway_grade_entry"))
        self.assertTemplateUsed(response, "pathway_grades/pathway_grade_entry.html")
        self.assertIsNone(response.context["form"])


class ExtraGradeViewsTests(PathwayFixturesMixin, LoggedInTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.extra = ExamType.objects.create(
            name="Nota extra", code="EX", kind=ExamKind.BONUS, max_score=Decimal(1)
        )
        cls.math = Subject.objects.create(name="Matemática")
        GradeLevelSubject.objects.create(grade_level=1, subject=cls.math)
        session = PathwaySession.objects.create(
            offering=cls.offering, date=date(2027, 3, 1)
        )
        PathwayAttendance.objects.create(session=session, pathway_enrollment=cls.member)
        PathwayGrade.objects.create(
            pathway_enrollment=cls.member, bimester=1, score=Decimal("0.5")
        )

    def setUp(self):
        super().setUp()
        # The fixtures' school year is 2027
        today = patch("django.utils.timezone.localdate", return_value=date(2027, 3, 1))
        today.start()
        self.addCleanup(today.stop)

    def extra_scores(self):
        return dict(
            Grade.objects.filter(exam_type=self.extra, bimester=1).values_list(
                "enrollment", "score"
            )
        )

    def test_individual(self):
        url = (
            f"{reverse('pathways:extra_grades_individual')}"
            f"?enrollment={self.enrollment.pk}&bimester=1"
        )
        response = self.client.get(url, **HTMX)
        self.assertTemplateUsed(
            response, "extra_grades/partials/extra_grades_subjects.html"
        )
        self.assertContains(response, "Matemática")

        response = self.client.post(url)
        self.assertRedirects(response, url)
        self.assertEqual(self.extra_scores(), {self.enrollment.pk: Decimal("0.5")})

    def test_all_calculates_the_current_year(self):
        url = reverse("pathways:extra_grades_all")
        response = self.client.post(url, {"bimester": 1})
        self.assertRedirects(response, f"{url}?bimester=1")
        self.assertEqual(
            self.extra_scores(),
            {self.enrollment.pk: Decimal("0.5"), self.other.pk: Decimal(0)},
        )

        response = self.client.get(url, {"bimester": 1}, **HTMX)
        self.assertTemplateUsed(
            response, "extra_grades/partials/extra_grades_table.html"
        )
        self.assertContains(response, "0,50")

    def test_missing_exam_type(self):
        self.extra.code = "XX"
        self.extra.save()
        url = reverse("pathways:extra_grades_all")
        response = self.client.post(url, {"bimester": 1}, follow=True)
        self.assertContains(response, "sigla EX")
        self.assertEqual(self.extra_scores(), {})


class PathwayPagesRenderTests(PathwayFixturesMixin, LoggedInTestCase):
    def test_every_page_renders(self):
        session = PathwaySession.objects.create(
            offering=self.offering, date=date(2027, 3, 1)
        )
        offering = {"offering": self.offering.pk}
        pages = [
            ("pathways:pathway_list", [], {}),
            ("pathways:pathway_add", [], {}),
            ("pathways:pathway_edit", [self.robotics.pk], {}),
            ("pathways:pathway_delete", [self.robotics.pk], {}),
            ("pathways:pathway_offering_list", [], {}),
            ("pathways:pathway_offering_add", [], {}),
            ("pathways:pathway_offering_edit", [self.offering.pk], {}),
            ("pathways:pathway_offering_delete", [self.offering.pk], {}),
            ("pathways:pathway_enrollment_list", [], offering),
            ("pathways:pathway_enrollment_add", [], offering),
            ("pathways:pathway_enrollment_edit", [self.member.pk], {}),
            ("pathways:pathway_enrollment_delete", [self.member.pk], {}),
            ("pathways:pathway_session_list", [], offering),
            ("pathways:pathway_session_add", [], offering),
            ("pathways:pathway_session_edit", [session.pk], {}),
            ("pathways:pathway_session_delete", [session.pk], {}),
            ("pathways:pathway_session_attendance", [session.pk], {}),
            ("pathways:pathway_grade_entry", [], {**offering, "bimester": 1}),
            ("pathways:extra_grades_individual", [], {}),
            ("pathways:extra_grades_all", [], {}),
            ("pathways:extra_grade_settings_list", [], {}),
        ]
        for name, args, params in pages:
            with self.subTest(name):
                response = self.client.get(reverse(name, args=args), params)
                self.assertEqual(response.status_code, 200)
