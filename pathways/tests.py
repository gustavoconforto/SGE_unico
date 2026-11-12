from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.urls import reverse

from base.testing import LoggedInTestCase
from enrollments.models import (
    Enrollment,
    EnrollmentStatus,
    EnrollmentType,
    SchoolYear,
)
from grades.models import ExamKind, ExamType, Grade, GradeLevelSubject, Subject
from incidents.tests import create_enrollment
from pathways.forms import StudentPathwaysForm
from pathways.models import (
    AttendanceStatus,
    Pathway,
    PathwayAttendance,
    PathwayEnrollment,
    PathwayGrade,
    PathwayOffering,
    PathwaySession,
    WorkloadType,
)
from pathways.services import (
    extra_grades,
    lesson_days,
    save_extra_grades,
    year_workload,
)
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


class WorkloadTests(PathwayFixturesMixin, LoggedInTestCase):
    def roll(self, statuses):
        for day, status in enumerate(statuses, start=2):
            session = PathwaySession.objects.create(
                offering=self.offering, date=date(2027, 3, day)
            )
            PathwayAttendance.objects.create(
                session=session, pathway_enrollment=self.member, status=status
            )

    def set_workload(self, workload_type, hours=Decimal(0)):
        self.robotics.workload_type = workload_type
        self.robotics.workload_hours = hours
        self.robotics.save()

    def test_no_workload_earns_nothing(self):
        self.roll([AttendanceStatus.PRESENT])
        self.assertEqual(year_workload(self.enrollment), 0)

    def test_fixed_workload_ignores_absences(self):
        self.set_workload(WorkloadType.FIXED, Decimal(40))
        self.roll([AttendanceStatus.ABSENT, AttendanceStatus.ABSENT])
        self.assertEqual(year_workload(self.enrollment), Decimal(40))

    def test_attendance_workload_counts_45_minutes_per_presence(self):
        self.set_workload(WorkloadType.ATTENDANCE)
        P, F, J = (
            AttendanceStatus.PRESENT,
            AttendanceStatus.ABSENT,
            AttendanceStatus.EXCUSED,
        )
        self.roll([P, P, P, F, J])
        self.assertEqual(year_workload(self.enrollment), Decimal("2.25"))

    def test_total_adds_every_pathway_of_the_year(self):
        self.set_workload(WorkloadType.ATTENDANCE)
        self.roll([AttendanceStatus.PRESENT])
        self.theater.workload_type = WorkloadType.FIXED
        self.theater.workload_hours = Decimal(20)
        self.theater.save()
        PathwayEnrollment.objects.create(
            enrollment=self.enrollment,
            offering=PathwayOffering.objects.create(
                pathway=self.theater, school_year=self.school_year
            ),
            joined_at=date(2027, 2, 1),
            left_at=date(2027, 2, 10),  # left early: fixed hours still count
        )
        self.assertEqual(year_workload(self.enrollment), Decimal("20.75"))
        self.assertEqual(year_workload(self.other), 0)

    def test_fixed_workload_needs_hours(self):
        self.robotics.workload_type = WorkloadType.FIXED
        with self.assertRaisesMessage(ValidationError, "Informe as horas"):
            self.robotics.full_clean()

    def test_other_types_drop_the_hours(self):
        self.robotics.workload_type = WorkloadType.ATTENDANCE
        self.robotics.workload_hours = Decimal(10)
        self.robotics.full_clean()
        self.assertEqual(self.robotics.workload_hours, 0)


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

    def test_q_and_a_sessions_dont_count(self):
        self.grade(self.member, "0.4")
        self.q_and_as(5)
        self.assertEqual(self.extra_of(self.enrollment), Decimal("0.40"))

    def test_pathway_grades_add_up_to_the_exam_maximum(self):
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

        self.extra.max_score = Decimal("0.6")
        self.assertEqual(self.extra_of(self.enrollment), Decimal("0.6"))

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

        skipped = save_extra_grades([self.enrollment, self.other], 1, self.extra)

        self.assertEqual(skipped, [])
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


class PathwayViewsTests(LoggedInTestCase):
    def test_crud(self):
        response = self.client.post(
            reverse("pathways:pathway_add"),
            {
                "name": "Robótica",
                "extra_points": "0.5",
                "workload_type": "N",
                "workload_hours": "0",
                "description": "",
            },
        )
        self.assertRedirects(response, reverse("pathways:pathway_list"))
        pathway = Pathway.objects.get()

        response = self.client.post(
            reverse("pathways:pathway_edit", args=[pathway.pk]),
            {
                "name": "Robótica avançada",
                "extra_points": "1",
                "workload_type": "F",
                "workload_hours": "40",
                "description": "",
            },
        )
        self.assertRedirects(response, reverse("pathways:pathway_list"))
        pathway.refresh_from_db()
        self.assertEqual(pathway.extra_points, Decimal(1))
        self.assertEqual(pathway.workload_hours, Decimal(40))

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
            f"?school_year={self.offering.school_year_id}"
            f"&offering={self.offering.pk}&bimester={bimester}"
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

    def test_offering_of_another_year_shows_no_sheet(self):
        other = SchoolYear.objects.exclude(pk=self.offering.school_year_id).first()
        url = self.sheet_url().replace(
            f"school_year={self.offering.school_year_id}",
            f"school_year={other.pk if other else 0}",
        )
        response = self.client.get(url, **HTMX)
        self.assertIsNone(response.context["form"])

    def test_offering_list_links_to_its_sheet(self):
        response = self.client.get(reverse("pathways:pathway_offering_list"))
        link = (
            f"{reverse('pathways:pathway_grade_entry')}"
            f"?school_year={self.offering.school_year_id}&offering={self.offering.pk}"
        )
        self.assertContains(response, link)

    def test_options_lists_offerings_of_the_year(self):
        url = reverse("pathways:pathway_grade_options")
        response = self.client.get(
            url, {"school_year": self.offering.school_year_id}, **HTMX
        )
        self.assertIn(
            self.offering, response.context["select_form"].fields["offering"].queryset
        )
        self.assertIn("school_year=", response["HX-Push-Url"])
        response = self.client.get(url, **HTMX)
        self.assertFalse(response.context["select_form"].fields["offering"].queryset)

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
        self.assertContains(response, "Calcular 1º bimestre para todos os alunos")

    def test_all_shows_and_calculates_the_chosen_year(self):
        other = SchoolYear.objects.create(
            begins=date(2028, 1, 10), ends=date(2028, 12, 15)
        )
        url = reverse("pathways:extra_grades_all")
        response = self.client.get(
            url, {"bimester": 1, "school_year": other.pk}, **HTMX
        )
        self.assertEqual(response.context["school_year"], other)
        self.assertFalse(response.context["enrollments"])

        response = self.client.post(url, {"bimester": 1, "school_year": other.pk})
        self.assertRedirects(response, f"{url}?bimester=1&school_year={other.pk}")
        self.assertEqual(self.extra_scores(), {})

    def test_all_names_the_students_left_without_grade(self):
        Enrollment.objects.filter(pk=self.other.pk).update(school_class=None)
        url = reverse("pathways:extra_grades_all")
        response = self.client.post(url, {"bimester": 1}, follow=True)
        self.assertContains(response, "Sem nota: Bruno Lima (sem turma).")
        self.assertEqual(self.extra_scores(), {self.enrollment.pk: Decimal("0.5")})

    def test_all_says_the_bimester_has_no_dates(self):
        url = reverse("pathways:extra_grades_all")
        response = self.client.post(url, {"bimester": 2}, follow=True)
        self.assertContains(response, "não tem as datas do 2º bimestre")

    def test_all_page_has_the_year_select(self):
        response = self.client.get(reverse("pathways:extra_grades_all"))
        self.assertContains(response, 'name="school_year"')
        self.assertEqual(response.context["school_year"], self.school_year)

    def test_all_page_has_the_bimester_select(self):
        response = self.client.get(reverse("pathways:extra_grades_all"))
        self.assertContains(response, 'name="bimester"')
        self.assertNotContains(response, "para todos os alunos")

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
            (
                "pathways:pathway_grade_entry",
                [],
                {
                    **offering,
                    "school_year": self.offering.school_year_id,
                    "bimester": 1,
                },
            ),
            ("pathways:pathway_grade_options", [], {}),
            ("pathways:extra_grades_individual", [], {}),
            ("pathways:extra_grades_all", [], {}),
        ]
        for name, args, params in pages:
            with self.subTest(name):
                response = self.client.get(reverse(name, args=args), params)
                self.assertEqual(response.status_code, 200)


class PathwayEnrollmentByStudentTests(PathwayFixturesMixin, LoggedInTestCase):
    TODAY = date(2027, 3, 1)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.theater_offering = PathwayOffering.objects.create(
            pathway=cls.theater, school_year=cls.school_year, capacity=1
        )

    def url(self, enrollment):
        return (
            f"{reverse('pathways:pathway_enrollment_by_student')}"
            f"?enrollment={enrollment.pk}"
        )

    def post(self, enrollment, *offerings):
        with patch("pathways.forms.timezone.localdate", return_value=self.TODAY):
            return self.client.post(
                self.url(enrollment), {f"offering_{o.pk}": "on" for o in offerings}
            )

    def test_lists_the_offerings_of_the_enrollment_year(self):
        PathwayOffering.objects.create(
            pathway=self.theater,
            school_year=SchoolYear.objects.create(
                begins=date(2028, 1, 10), ends=date(2028, 12, 15)
            ),
        )
        response = self.client.get(
            reverse("pathways:pathway_enrollment_by_student"),
            {"enrollment": self.enrollment.pk},
            **HTMX,
        )
        self.assertTemplateUsed(
            response,
            "pathway_enrollments/partials/pathway_enrollment_by_student_sheet.html",
        )
        form = response.context["form"]
        self.assertEqual(form.offerings, [self.offering, self.theater_offering])
        self.assertTrue(form[f"offering_{self.offering.pk}"].initial)

    def test_without_enrollment_shows_only_the_select(self):
        response = self.client.get(reverse("pathways:pathway_enrollment_by_student"))
        self.assertIsNone(response.context["form"])

    def test_join_leave_and_rejoin(self):
        response = self.post(self.other, self.offering, self.theater_offering)
        self.assertRedirects(response, self.url(self.other))
        joined = PathwayEnrollment.objects.filter(enrollment=self.other)
        self.assertEqual(joined.count(), 2)
        self.assertEqual({m.joined_at for m in joined}, {self.TODAY})

        self.post(self.other, self.theater_offering)
        left = PathwayEnrollment.objects.get(
            enrollment=self.other, offering=self.offering
        )
        self.assertEqual(left.left_at, self.TODAY)

        self.post(self.other, self.offering, self.theater_offering)
        left.refresh_from_db()
        self.assertIsNone(left.left_at)

    def test_leaving_before_starting_deletes(self):
        self.member.joined_at = date(2027, 4, 1)
        self.member.save()
        self.post(self.enrollment)
        self.assertFalse(PathwayEnrollment.objects.filter(pk=self.member.pk).exists())

    def test_full_offering_saves_nothing(self):
        PathwayEnrollment.objects.create(
            enrollment=self.enrollment, offering=self.theater_offering
        )
        form = self.client.get(self.url(self.other)).context["form"]
        self.assertTrue(form[f"offering_{self.theater_offering.pk}"].field.disabled)

        # Seat taken after the page was loaded: the disabled box is ignored.
        response = self.post(self.other, self.offering, self.theater_offering)
        self.assertRedirects(response, self.url(self.other))
        self.assertFalse(
            PathwayEnrollment.objects.filter(
                enrollment=self.other, offering=self.theater_offering
            ).exists()
        )

    def test_capacity_error_rolls_back(self):
        form = StudentPathwaysForm(
            {
                f"offering_{self.offering.pk}": "on",
                f"offering_{self.theater_offering.pk}": "on",
            },
            enrollment=self.other,
        )
        # Someone takes the last seat between rendering and saving.
        PathwayEnrollment.objects.create(
            enrollment=self.enrollment, offering=self.theater_offering
        )
        self.assertFalse(form.is_valid())
        self.assertIn(f"offering_{self.theater_offering.pk}", form.errors)
        self.assertFalse(
            PathwayEnrollment.objects.filter(enrollment=self.other).exists()
        )

    def test_inactive_enrollment_is_rejected(self):
        Enrollment.objects.filter(pk=self.other.pk).update(
            status=EnrollmentStatus.COMPLETED
        )
        response = self.client.get(self.url(self.other))
        self.assertIsNone(response.context["form"])


class PathwayDiaryTests(PathwayFixturesMixin, LoggedInTestCase):
    def url(self, bimester=1):
        return (
            f"{reverse('pathways:pathway_offering_diary', args=[self.offering.pk])}"
            f"?bimester={bimester}"
        )

    def setUp(self):
        super().setUp()
        self.offering.weekdays = [2, 4]
        self.offering.save()

    def test_lesson_days_follow_the_weekdays(self):
        days = lesson_days(self.offering, date(2027, 2, 1), date(2027, 4, 15))
        self.assertEqual(len(days), 22)
        self.assertEqual((days[0], days[-1]), (date(2027, 2, 2), date(2027, 4, 15)))
        self.assertEqual({day.isoweekday() for day in days}, {2, 4})

    def test_diary_lists_members_and_days(self):
        PathwayEnrollment.objects.create(
            enrollment=self.other,
            offering=self.offering,
            joined_at=date(2027, 2, 1),
            left_at=date(2027, 2, 3),
        )
        response = self.client.get(self.url())
        self.assertTemplateUsed(
            response, "pathway_offerings/pathway_offering_diary.html"
        )
        self.assertEqual(len(response.context["days"]), 22)
        rows = dict(response.context["rows"])
        self.assertEqual(set(rows), {self.member, self.other.pathway_enrollments.get()})
        self.assertTrue(all(rows[self.member]))
        left = rows[self.other.pathway_enrollments.get()]
        self.assertEqual(left[:2], [True, False])
        self.assertContains(response, "Robótica")

    def test_missing_weekdays_or_dates(self):
        self.offering.weekdays = []
        self.offering.save()
        self.assertContains(self.client.get(self.url()), "Defina os dias de aula")
        self.assertContains(
            self.client.get(self.url(bimester=2)), "não tem as datas deste bimestre"
        )

    def test_offering_list_links_to_the_diary(self):
        response = self.client.get(reverse("pathways:pathway_offering_list"))
        self.assertContains(
            response,
            reverse("pathways:pathway_offering_diary", args=[self.offering.pk]),
        )

    def test_form_saves_weekdays(self):
        data = {
            "pathway": self.theater.pk,
            "school_year": self.school_year.pk,
            "weekdays": ["4", "2"],
        }
        response = self.client.post(reverse("pathways:pathway_offering_add"), data)
        self.assertRedirects(response, reverse("pathways:pathway_offering_list"))
        offering = PathwayOffering.objects.get(pathway=self.theater)
        self.assertEqual(offering.weekdays, [2, 4])

        data["weekdays"] = ["7"]
        response = self.client.post(reverse("pathways:pathway_offering_add"), data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors["weekdays"])


class StudentAttendanceTests(PathwayFixturesMixin, LoggedInTestCase):
    def url(self, bimester=1):
        return (
            f"{reverse('pathways:student_attendance')}"
            f"?enrollment={self.enrollment.pk}&bimester={bimester}"
        )

    def roll(self, day, status, member=None):
        session = PathwaySession.objects.create(offering=self.offering, date=day)
        PathwayAttendance.objects.create(
            session=session, pathway_enrollment=member or self.member, status=status
        )

    def test_counts_and_days_in_the_bimester(self):
        self.roll(date(2027, 2, 2), AttendanceStatus.PRESENT)
        self.roll(date(2027, 2, 9), AttendanceStatus.ABSENT)
        self.roll(date(2027, 3, 2), AttendanceStatus.ABSENT)
        self.roll(date(2027, 3, 9), AttendanceStatus.EXCUSED)
        self.roll(date(2027, 5, 4), AttendanceStatus.ABSENT)  # after the bimester
        response = self.client.get(self.url())
        self.assertTemplateUsed(response, "pathway_attendance/student_attendance.html")
        [row] = response.context["rows"]
        self.assertEqual((row.present, row.absent, row.excused), (1, 2, 1))
        self.assertEqual(row.absent_days, [date(2027, 2, 9), date(2027, 3, 2)])
        self.assertEqual(row.excused_days, [date(2027, 3, 9)])
        self.assertContains(response, "fev ·</span> 09</div>", html=False)
        self.assertContains(response, "mar ·</span> 02</div>", html=False)

    def test_shows_the_year_workload(self):
        self.robotics.workload_type = WorkloadType.FIXED
        self.robotics.workload_hours = Decimal("12.5")
        self.robotics.save()
        response = self.client.get(self.url())
        self.assertEqual(response.context["year_workload"], Decimal("12.5"))
        self.assertContains(response, "12,50 h")

    def test_lists_only_pathways_joined_during_the_bimester(self):
        theater = PathwayOffering.objects.create(
            pathway=self.theater, school_year=self.school_year
        )
        PathwayEnrollment.objects.create(
            enrollment=self.enrollment,
            offering=theater,
            joined_at=date(2027, 1, 10),
            left_at=date(2027, 1, 20),
        )
        response = self.client.get(self.url())
        self.assertEqual(list(response.context["rows"]), [self.member])

    def test_empty_selection_and_missing_dates(self):
        response = self.client.get(reverse("pathways:student_attendance"))
        self.assertContains(response, "Selecione um aluno e um bimestre")
        self.assertContains(self.client.get(self.url(bimester=2)), "não tem as datas")

    def test_htmx_renders_the_partial(self):
        response = self.client.get(self.url(), HTTP_HX_REQUEST="true")
        self.assertTemplateUsed(
            response, "pathway_attendance/partials/student_attendance_table.html"
        )
        self.assertTemplateNotUsed(
            response, "pathway_attendance/student_attendance.html"
        )


class StudentWorkloadTests(PathwayFixturesMixin, LoggedInTestCase):
    def url(self, enrollment=None):
        url = reverse("pathways:student_workload")
        return f"{url}?enrollment={enrollment.pk}" if enrollment else url

    def test_lists_each_pathway_with_its_hours_and_the_total(self):
        self.robotics.workload_type = WorkloadType.ATTENDANCE
        self.robotics.save()
        for day, status in [
            (date(2027, 3, 2), AttendanceStatus.PRESENT),
            (date(2027, 3, 9), AttendanceStatus.PRESENT),
            (date(2027, 3, 16), AttendanceStatus.ABSENT),
        ]:
            PathwayAttendance.objects.create(
                session=PathwaySession.objects.create(offering=self.offering, date=day),
                pathway_enrollment=self.member,
                status=status,
            )
        self.theater.workload_type = WorkloadType.FIXED
        self.theater.workload_hours = Decimal(20)
        self.theater.save()
        theater = PathwayEnrollment.objects.create(
            enrollment=self.enrollment,
            offering=PathwayOffering.objects.create(
                pathway=self.theater, school_year=self.school_year
            ),
            joined_at=date(2027, 2, 1),
        )
        PathwayEnrollment.objects.create(  # another student's pathway
            enrollment=self.other, offering=self.offering, joined_at=date(2027, 2, 1)
        )

        response = self.client.get(self.url(self.enrollment))
        self.assertTemplateUsed(response, "pathway_workloads/student_workload.html")
        rows = response.context["pathway_enrollments"]
        self.assertEqual(rows, [self.member, theater])
        self.assertEqual([row.workload for row in rows], [Decimal("1.5"), 20])
        self.assertEqual(response.context["total_workload"], Decimal("21.5"))
        self.assertContains(response, "21,50 h")

    def test_asks_for_a_student_first(self):
        response = self.client.get(self.url())
        self.assertContains(response, "Selecione um aluno para ver a carga horária")
        self.assertNotIn("enrollment", response.context)

    def test_htmx_renders_the_partial(self):
        response = self.client.get(self.url(self.enrollment), **HTMX)
        self.assertTemplateUsed(
            response, "pathway_workloads/partials/student_workload_table.html"
        )
        self.assertTemplateNotUsed(response, "pathway_workloads/student_workload.html")

    def test_print_report(self):
        self.robotics.workload_type = WorkloadType.FIXED
        self.robotics.workload_hours = Decimal(30)
        self.robotics.save()
        self.assertContains(
            self.client.get(self.url(self.enrollment)),
            reverse("pathways:student_workload_print", args=[self.enrollment.pk]),
        )

        response = self.client.get(
            reverse("pathways:student_workload_print", args=[self.enrollment.pk])
        )
        self.assertTemplateUsed(
            response, "pathway_workloads/student_workload_print.html"
        )
        self.assertEqual(response.context["rows"], [self.member])
        self.assertEqual(response.context["total_workload"], Decimal(30))
        self.assertContains(response, self.enrollment.student.name)
        self.assertContains(response, "unico_logo_stamp.png")
        self.assertContains(response, "30,00 h")

    def test_print_report_without_pathways(self):
        response = self.client.get(
            reverse("pathways:student_workload_print", args=[self.other.pk])
        )
        self.assertContains(response, "não participou de nenhum itinerário")
