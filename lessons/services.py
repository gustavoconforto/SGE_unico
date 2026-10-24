from collections import Counter
from typing import NamedTuple

from grades.models import GradeLevelSubject
from lessons.models import PERIODS, TimetableSlot, Weekday


class WeeklyLoad(NamedTuple):
    subject: GradeLevelSubject
    scheduled: int
    expected: object  # Decimal or None
    matches: bool


def timetable_grid(school_class):
    """[(period label, [slot or None per weekday])] of the class's timetable."""
    slots = {
        (slot.weekday, slot.period): slot
        for slot in TimetableSlot.objects.filter(
            school_class=school_class
        ).select_related("subject__subject", "teacher")
    }
    return [
        (label, [slots.get((weekday, period)) for weekday in Weekday.values])
        for period, label in PERIODS
    ]


def weekly_load(school_class):
    """Periods scheduled per subject of the class's series against its
    `weekly_classes`; a weekly mean, so a mismatch is only a warning."""
    scheduled = Counter(
        TimetableSlot.objects.filter(school_class=school_class).values_list(
            "subject_id", flat=True
        )
    )
    return [
        WeeklyLoad(
            subject,
            scheduled[subject.pk],
            subject.weekly_classes,
            subject.weekly_classes is None
            or scheduled[subject.pk] == subject.weekly_classes,
        )
        for subject in GradeLevelSubject.objects.filter(
            grade_level=school_class.grade_level
        ).select_related("subject")
    ]
