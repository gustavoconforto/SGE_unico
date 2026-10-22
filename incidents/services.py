"""Behaviour ("conceito") grade of a bimester, computed from incidents and delays."""

from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Sum

from grades.models import ExamType, Grade, GradeLevelSubject
from incidents.models import Incident, StudentDelay, StudentDelayType

ZERO = Decimal(0)
CONCEPT_CODE = "C"
CONCEPT_START = Decimal(1)
# Tolerated delays beyond this count cost DELAY_PENALTY each.
TOLERATED_DELAYS = 2
DELAY_PENALTY = Decimal("0.2")


def concept_exam_type():
    return ExamType.objects.filter(code=CONCEPT_CODE).first()


def bimester_range(school_year, bimester):
    """(begins, ends) of the bimester, or None when the school year lacks its dates."""
    begins = getattr(school_year, f"bi_{bimester}_begins")
    ends = getattr(school_year, f"bi_{bimester}_ends")
    return (begins, ends) if begins and ends else None


def concept_grade(penalties, acceptable_delays):
    extra_delays = max(acceptable_delays - TOLERATED_DELAYS, 0)
    return max(CONCEPT_START - penalties - DELAY_PENALTY * extra_delays, ZERO)


def concept_grades(enrollments, bimester):
    """{enrollment pk: concept grade} for the bimester.

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
        penalties = dict(
            Incident.objects.filter(
                enrollment_id__in=ids, incident_date__range=date_range
            )
            .order_by()
            .values("enrollment")
            .annotate(total=Sum("incident_type__penalty"))
            .values_list("enrollment", "total")
        )
        delays = dict(
            StudentDelay.objects.filter(
                enrollment_id__in=ids,
                incident_date__range=date_range,
                delay_type=StudentDelayType.ACCEPTABLE,
            )
            .order_by()
            .values("enrollment")
            .annotate(total=Count("pk"))
            .values_list("enrollment", "total")
        )
        for pk in ids:
            grades[pk] = concept_grade(penalties.get(pk, ZERO), delays.get(pk, 0))
    return grades


def save_concept_grades(enrollments, bimester, exam_type):
    """Give every subject of each enrollment's series its concept grade.

    Returns the number of enrollments graded; those without bimester dates or
    without subjects (no class or series) are skipped.
    """
    grades = concept_grades(enrollments, bimester)
    subjects_by_level = defaultdict(list)
    for level, subject_id in GradeLevelSubject.objects.values_list(
        "grade_level", "subject_id"
    ):
        subjects_by_level[level].append(subject_id)

    rows = []
    graded = 0
    for enrollment in enrollments:
        school_class = enrollment.school_class
        subject_ids = (
            subjects_by_level[school_class.grade_level] if school_class else []
        )
        if enrollment.pk not in grades or not subject_ids:
            continue
        graded += 1
        rows += [
            Grade(
                enrollment=enrollment,
                subject_id=subject_id,
                exam_type=exam_type,
                bimester=bimester,
                score=grades[enrollment.pk],
            )
            for subject_id in subject_ids
        ]
    with transaction.atomic():
        Grade.objects.bulk_create(
            rows,
            update_conflicts=True,
            unique_fields=["enrollment", "subject", "exam_type", "bimester"],
            update_fields=["score", "updated_at"],
        )
    return graded
