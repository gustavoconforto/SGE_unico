"""Grade calculation for the report card.

Grades are computed from the scores on every request, never stored, so a
corrected score is reflected everywhere at once.

Bimester grade: sum of the regular exams and the bonus points (each exam's
max_score is its share, e.g. PS 3 + PB 6 + behavior 1), capped at MAX_GRADE so
extra points can't go past 10.
Annual average: weighted mean of the four bimester grades (20%, 30%, 20%,
30%), only once all four exist, rounded to the nearest half point: below .25
goes down to .0, from .25 up to .5, from .75 up to the next whole grade.
Final grade: the annual average; below PASSING_GRADE the student takes the
final recovery exam, and the final grade becomes the mean of the average and
the recovery score, rounded the same way. The student passes with a final
grade of at least PASSING_GRADE.
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from grades.models import (
    FINAL_RECOVERY,
    Bimester,
    ExamKind,
    Grade,
    GradeLevelSubject,
)

MAX_GRADE = Decimal("10.00")
PASSING_GRADE = Decimal("6.00")
CENTS = Decimal("0.01")
HALF = Decimal("0.5")
BIMESTER_WEIGHTS = (Decimal("0.2"), Decimal("0.3"), Decimal("0.2"), Decimal("0.3"))


def _round(value):
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


def _round_to_half(value):
    """Round to .0 or .5, with .25 and .75 as the thresholds (7.24 -> 7.0,
    7.25 -> 7.5, 7.75 -> 8.0)."""
    halves = (value / HALF).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return _round(halves * HALF)


def bimester_grade(grades):
    """Grade of one subject in one bimester; None without regular grades.

    `grades` are Grade objects with `exam_type` loaded (select_related).
    Recovery grades don't count: recovery is the final exam, not a bimester's.
    """
    total = Decimal(0)
    has_regular = False
    for grade in grades:
        kind = grade.exam_type.kind
        if kind == ExamKind.RECOVERY:
            continue
        total += grade.score
        has_regular = has_regular or kind == ExamKind.REGULAR

    if not has_regular:
        return None
    return _round(min(total, MAX_GRADE))


def recovery_score(grades):
    """Best recovery score among `grades`; None without one."""
    return max(
        (grade.score for grade in grades if grade.exam_type.kind == ExamKind.RECOVERY),
        default=None,
    )


def final_average(bimester_grades):
    """Weighted mean of the four bimester grades, rounded to the nearest half
    point; None while any of them is missing."""
    if len(bimester_grades) < len(Bimester) or None in bimester_grades:
        return None
    return _round_to_half(
        sum(
            grade * weight
            for grade, weight in zip(bimester_grades, BIMESTER_WEIGHTS, strict=True)
        )
    )


def needs_recovery(average):
    return average is not None and average < PASSING_GRADE


def final_grade(average, recovery):
    """Mean of the annual average and the recovery score, rounded to the
    nearest half point, for a student below the passing grade; the average
    itself otherwise or while there is no recovery score."""
    if not needs_recovery(average) or recovery is None:
        return average
    return _round_to_half((average + recovery) / 2)


def annual_averages(enrollments, subject):
    """Annual average of `subject` per enrollment pk, in one query."""
    grouped = {}
    for grade in Grade.objects.filter(
        enrollment__in=enrollments, subject=subject, bimester__in=Bimester.values
    ).select_related("exam_type"):
        grouped.setdefault((grade.enrollment_id, grade.bimester), []).append(grade)
    return {
        enrollment.pk: final_average(
            [
                bimester_grade(grouped.get((enrollment.pk, bimester), []))
                for bimester in Bimester.values
            ]
        )
        for enrollment in enrollments
    }


@dataclass
class ReportCardRow:
    subject: object
    bimesters: list = field(default_factory=list)  # one grade or None per bimester
    # Per bimester, the score (or None) of each exam passed to report_card().
    exam_scores: list = field(default_factory=list)
    average: Decimal | None = None
    recovery: Decimal | None = None

    @property
    def bimester_details(self):
        """(exam scores, bimester grade) per bimester."""
        return list(zip(self.exam_scores, self.bimesters, strict=True))

    @property
    def needs_recovery(self):
        return needs_recovery(self.average)

    @property
    def final(self):
        return final_grade(self.average, self.recovery)

    @property
    def passed(self):
        """None while the year or the recovery exam is still to come."""
        if self.average is None or (self.needs_recovery and self.recovery is None):
            return None
        return self.final >= PASSING_GRADE


def report_card(enrollment, exam_types=()):
    """One row per subject of the enrollment's series, in two queries.

    With `exam_types`, each row's `exam_scores` also holds, per bimester, the
    score of each of those exams in their order.
    """
    school_class = enrollment.school_class
    level_subjects = GradeLevelSubject.objects.filter(
        grade_level=school_class.grade_level if school_class else None
    ).select_related("subject")

    grouped = {}
    for grade in Grade.objects.filter(enrollment=enrollment).select_related(
        "exam_type"
    ):
        grouped.setdefault((grade.subject_id, grade.bimester), []).append(grade)

    rows = []
    for level_subject in level_subjects:
        periods = [
            grouped.get((level_subject.subject_id, bimester), [])
            for bimester in Bimester.values
        ]
        grades = [bimester_grade(period) for period in periods]
        scores = [
            {grade.exam_type_id: grade.score for grade in period} for period in periods
        ]
        rows.append(
            ReportCardRow(
                subject=level_subject.subject,
                bimesters=grades,
                exam_scores=[
                    [by_exam.get(exam_type.pk) for exam_type in exam_types]
                    for by_exam in scores
                ],
                average=final_average(grades),
                recovery=recovery_score(
                    grouped.get((level_subject.subject_id, FINAL_RECOVERY), [])
                ),
            )
        )
    return rows
