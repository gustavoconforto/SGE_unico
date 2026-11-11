"""Extra grade ("nota extra") of a bimester, from the pathways.

The pathway teachers' grades of the bimester are added as they are; a pathway
without a grade adds nothing, and attendance is only shown, never counted. The
total is capped at the extra exam type's maximum and written to every subject
of the student's series, like the concept grade. Q&A sessions don't count:
their grades are entered by hand.
"""

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum

from grades.models import ExamType
from grades.services import save_series_grades
from incidents.services import bimester_range
from pathways.models import AttendanceStatus, PathwayGrade

ZERO = Decimal(0)
EXTRA_CODE = "EX"


def lesson_days(offering, begins, ends):
    """The dates from `begins` to `ends` that fall on the offering's weekdays."""
    weekdays = set(offering.weekdays)
    return [
        day
        for day in (begins + timedelta(n) for n in range((ends - begins).days + 1))
        if day.isoweekday() in weekdays
    ]


def extra_exam_type():
    return ExamType.objects.filter(code=EXTRA_CODE).first()


def attendance_rate(present, absent):
    """Percentage of lessons attended; None without lessons."""
    lessons = present + absent
    return Decimal(100) * present / lessons if lessons else None


def with_attendance(pathway_enrollments, date_range):
    """Annotate `present` and `absent`: the lessons in `date_range` attended
    and missed (excused absences are in neither)."""

    def lessons(status):
        return Count(
            "attendances",
            filter=Q(
                attendances__status=status,
                attendances__session__date__range=date_range,
            ),
        )

    return pathway_enrollments.annotate(
        present=lessons(AttendanceStatus.PRESENT),
        absent=lessons(AttendanceStatus.ABSENT),
    )


def pathways_points(enrollment_ids, bimester):
    """{enrollment pk: sum of its pathway grades in the bimester}.

    Grades left in a pathway that no longer gives an extra grade don't count.
    """
    totals = (
        PathwayGrade.objects.filter(
            pathway_enrollment__enrollment_id__in=enrollment_ids,
            pathway_enrollment__offering__pathway__extra_points__gt=0,
            bimester=bimester,
        )
        .values("pathway_enrollment__enrollment")
        .annotate(total=Sum("score"))
        .order_by()
        .values_list("pathway_enrollment__enrollment", "total")
    )
    return defaultdict(lambda: ZERO, totals)


def extra_grades(enrollments, bimester, exam_type):
    """{enrollment pk: extra grade} for the bimester, capped at the exam
    type's maximum.

    Enrollments whose school year has no dates for the bimester are left out.
    Expects `enrollment_type__school_year` selected.
    """
    ids_by_year = defaultdict(list)
    years = {}
    for enrollment in enrollments:
        school_year = enrollment.enrollment_type.school_year
        years[school_year.pk] = school_year
        ids_by_year[school_year.pk].append(enrollment.pk)

    grades = {}
    for year_id, ids in ids_by_year.items():
        date_range = bimester_range(years[year_id], bimester)
        if date_range is None:
            continue
        from_pathways = pathways_points(ids, bimester)
        for pk in ids:
            grades[pk] = min(from_pathways[pk], exam_type.max_score)
    return grades


def save_extra_grades(enrollments, bimester, exam_type):
    """Give every subject of each enrollment's series its extra grade, zero
    included, so a recalculation replaces outdated values.

    Returns the number of enrollments graded; those without bimester dates or
    without subjects (no class or series) are skipped.
    """
    return save_series_grades(
        enrollments, bimester, exam_type, extra_grades(enrollments, bimester, exam_type)
    )
