"""Grade calculation for the report card.

Grades are computed from the scores on every request, never stored, so a
corrected score is reflected everywhere at once.

Bimester grade:
    1. sum of the regular exams and the bonus points (each exam's max_score
       is its share, e.g. PS 3 + PB 6 + behavior 1), capped at MAX_GRADE so
       extra points can't go past 10;
    2. replaced by the recovery score when that is higher.
Final average: arithmetic mean of the four bimester grades, only once all
four exist.
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from grades.models import Bimester, ExamKind, Grade, GradeLevelSubject

MAX_GRADE = Decimal("10.00")
PASSING_GRADE = Decimal("6.00")
CENTS = Decimal("0.01")


def _round(value):
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


def bimester_grade(grades):
    """Grade of one subject in one bimester; None without regular grades.

    `grades` are Grade objects with `exam_type` loaded (select_related).
    """
    total = Decimal(0)
    has_regular = False
    recovery = None
    for grade in grades:
        kind = grade.exam_type.kind
        if kind == ExamKind.RECOVERY:
            recovery = grade.score if recovery is None else max(recovery, grade.score)
        else:
            total += grade.score
            has_regular = has_regular or kind == ExamKind.REGULAR

    if not has_regular:
        return None
    result = min(total, MAX_GRADE)
    if recovery is not None:
        result = max(result, recovery)
    return _round(result)


def final_average(bimester_grades):
    """Mean of the four bimester grades; None while any of them is missing."""
    if len(bimester_grades) < len(Bimester) or None in bimester_grades:
        return None
    return _round(sum(bimester_grades) / len(bimester_grades))


@dataclass
class ReportCardRow:
    subject: object
    bimesters: list = field(default_factory=list)  # one grade or None per bimester
    final: Decimal | None = None

    @property
    def passed(self):
        return None if self.final is None else self.final >= PASSING_GRADE


def report_card(enrollment):
    """One row per subject of the enrollment's series, in two queries."""
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
        grades = [
            bimester_grade(grouped.get((level_subject.subject_id, bimester), []))
            for bimester in Bimester.values
        ]
        rows.append(
            ReportCardRow(
                subject=level_subject.subject,
                bimesters=grades,
                final=final_average(grades),
            )
        )
    return rows
