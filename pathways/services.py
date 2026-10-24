"""Extra grade ("nota extra") of a bimester, from pathways and Q&A sessions.

Each pathway adds `score / 10 × pathway.extra_points` when the student's
attendance in the bimester's lessons reaches the year's minimum (excused
absences don't count either way); no lessons, no grade or low attendance add
nothing. Q&A sessions add their fixed points (`q_and_a.services`). The total is
capped at the extra exam type's maximum and written to every subject of the
student's series, like the concept grade.
"""

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, Q

from grades.models import ExamType
from grades.services import save_series_grades
from incidents.services import bimester_range
from pathways.models import (
    MAX_PATHWAY_SCORE,
    AttendanceStatus,
    ExtraGradeSettings,
    PathwayEnrollment,
)
from q_and_a.services import q_and_a_points

ZERO = Decimal(0)
CENTS = Decimal("0.01")
EXTRA_CODE = "EX"


def extra_exam_type():
    return ExamType.objects.filter(code=EXTRA_CODE).first()


def attendance_rate(present, absent):
    """Percentage of lessons attended; None without lessons."""
    lessons = present + absent
    return Decimal(100) * present / lessons if lessons else None


def pathway_points(score, extra_points, rate, settings):
    if score is None or rate is None or rate < settings.min_pathway_attendance:
        return ZERO
    return (score / MAX_PATHWAY_SCORE * extra_points).quantize(
        CENTS, rounding=ROUND_HALF_UP
    )


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


def pathways_points(enrollment_ids, bimester, date_range, settings):
    """{enrollment pk: points} from every pathway the enrollments joined."""
    pathway_enrollments = with_attendance(
        PathwayEnrollment.objects.filter(enrollment_id__in=enrollment_ids),
        date_range,
    ).select_related("offering__pathway")
    scores = dict(
        PathwayEnrollment.objects.filter(
            enrollment_id__in=enrollment_ids, grades__bimester=bimester
        ).values_list("pk", "grades__score")
    )
    points = defaultdict(lambda: ZERO)
    for pathway_enrollment in pathway_enrollments:
        points[pathway_enrollment.enrollment_id] += pathway_points(
            scores.get(pathway_enrollment.pk),
            pathway_enrollment.offering.pathway.extra_points,
            attendance_rate(pathway_enrollment.present, pathway_enrollment.absent),
            settings,
        )
    return points


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
        settings = ExtraGradeSettings.for_school_year(years[year_id])
        from_pathways = pathways_points(ids, bimester, date_range, settings)
        from_q_and_a = q_and_a_points(ids, date_range, settings)
        for pk in ids:
            grades[pk] = min(from_pathways[pk] + from_q_and_a[pk], exam_type.max_score)
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
