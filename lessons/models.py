from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from base.models import TimeStampedModel
from employees.models import Employee
from grades.models import GradeLevelSubject

LECTURES_PER_DAY = 12
SATURDAY_LECTURES = 7
PERIODS = [(period, f"{period}ª aula") for period in range(1, LECTURES_PER_DAY + 1)]


class Weekday(models.IntegerChoices):
    MONDAY = 1, "Segunda-feira"
    TUESDAY = 2, "Terça-feira"
    WEDNESDAY = 3, "Quarta-feira"
    THURSDAY = 4, "Quinta-feira"
    FRIDAY = 5, "Sexta-feira"
    SATURDAY = 6, "Sábado"


def weekday_periods(weekday):
    """The (period, label) choices of a weekday: Saturday has fewer."""
    if weekday == Weekday.SATURDAY:
        return PERIODS[:SATURDAY_LECTURES]
    return PERIODS


def period_error(weekday, period):
    """Why the weekday has no such period, or None."""
    if weekday == Weekday.SATURDAY and period > SATURDAY_LECTURES:
        return f"O sábado tem só {SATURDAY_LECTURES} aulas."
    return None


def lecture_teachers(level_subject):
    """Who may give a lecture of the subject: its teachers in the series or,
    as substitutes, any teacher of the subject's department."""
    return Employee.objects.filter(
        Q(grade_level_subjects=level_subject)
        | Q(departments__subjects=level_subject.subject_id)
    ).distinct()


def lecture_date_error(school_class, day):
    """Why `day` can't have lectures of the class, or None."""
    if day.isoweekday() > Weekday.SATURDAY:
        return "As aulas são de segunda a sábado."
    school_year = school_class.year
    if not school_year.begins <= day <= school_year.ends:
        return "A data está fora do ano escolar da turma."
    return None


class TimetableSlot(models.Model):
    """A period of the class's weekly timetable (grade horária)."""

    school_class = models.ForeignKey(
        "classes.Class",
        on_delete=models.PROTECT,
        related_name="timetable_slots",
        verbose_name="Turma",
    )
    weekday = models.PositiveSmallIntegerField("Dia da semana", choices=Weekday.choices)
    period = models.PositiveSmallIntegerField("Aula", choices=PERIODS)
    subject = models.ForeignKey(
        GradeLevelSubject,
        on_delete=models.PROTECT,
        related_name="timetable_slots",
        verbose_name="Matéria",
    )
    teacher = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="timetable_slots",
        verbose_name="Professor",
    )

    class Meta:
        verbose_name = "Horário da grade"
        verbose_name_plural = "Horários da grade"
        ordering = ["school_class", "weekday", "period"]
        constraints = [
            models.UniqueConstraint(
                fields=["school_class", "weekday", "period"],
                name="unique_timetable_slot",
            ),
            models.CheckConstraint(
                condition=Q(weekday__gte=1, weekday__lte=Weekday.SATURDAY),
                name="timetable_slot_weekday_range",
            ),
            models.CheckConstraint(
                condition=~Q(weekday=Weekday.SATURDAY)
                | Q(period__lte=SATURDAY_LECTURES),
                name="timetable_slot_saturday_period_range",
            ),
            models.CheckConstraint(
                condition=Q(period__gte=1, period__lte=LECTURES_PER_DAY),
                name="timetable_slot_period_range",
            ),
        ]

    def __str__(self):
        return f"{self.school_class} - {self.get_weekday_display()} - {self.get_period_display()}"

    def clean(self):
        errors = {}
        if self.weekday and self.period:
            message = period_error(self.weekday, self.period)
            if message:
                errors["period"] = message
        if self.school_class_id and self.subject_id:
            if self.subject.grade_level != self.school_class.grade_level:
                errors["subject"] = "Esta matéria não é oferecida na série da turma."
            elif (
                self.teacher_id
                and not self.subject.teachers.filter(pk=self.teacher_id).exists()
            ):
                errors["teacher"] = "Este professor não leciona esta matéria na série."
        if not errors and self.school_class_id and self.teacher_id:
            # Same period number in the same shift is the same time of day.
            clash = (
                TimetableSlot.objects.filter(
                    teacher_id=self.teacher_id,
                    weekday=self.weekday,
                    period=self.period,
                    school_class__year_id=self.school_class.year_id,
                    school_class__shift=self.school_class.shift,
                )
                .exclude(school_class_id=self.school_class_id)
                .select_related("school_class")
                .first()
            )
            if clash:
                errors["teacher"] = (
                    f"O professor já tem aula na turma {clash.school_class} neste horário."
                )
        if errors:
            raise ValidationError(errors)


class Lecture(TimeStampedModel):
    """A lecture given on a date (diário de classe). Subject and teacher are
    copied from the timetable, so substitutions don't change it."""

    school_class = models.ForeignKey(
        "classes.Class",
        on_delete=models.PROTECT,
        related_name="lectures",
        verbose_name="Turma",
    )
    date = models.DateField("Data")
    period = models.PositiveSmallIntegerField("Aula", choices=PERIODS)
    subject = models.ForeignKey(
        GradeLevelSubject,
        on_delete=models.PROTECT,
        related_name="lectures",
        verbose_name="Matéria",
    )
    teacher = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="lectures",
        verbose_name="Professor",
    )
    topic = models.CharField("Conteúdo", max_length=200)

    class Meta:
        verbose_name = "Aula"
        verbose_name_plural = "Aulas"
        ordering = ["-date", "school_class", "period"]
        constraints = [
            models.UniqueConstraint(
                fields=["school_class", "date", "period"], name="unique_lecture"
            ),
            models.CheckConstraint(
                condition=Q(period__gte=1, period__lte=LECTURES_PER_DAY),
                name="lecture_period_range",
            ),
        ]

    def __str__(self):
        return (
            f"{self.school_class} - {self.date:%d/%m/%Y} - {self.get_period_display()}"
        )

    def clean(self):
        errors = {}
        if self.school_class_id and self.date:
            message = lecture_date_error(self.school_class, self.date)
            if message:
                errors["date"] = message
        if self.date and self.period:
            message = period_error(self.date.isoweekday(), self.period)
            if message:
                errors["period"] = message
        if self.school_class_id and self.subject_id:
            if self.subject.grade_level != self.school_class.grade_level:
                errors["subject"] = "Esta matéria não é oferecida na série da turma."
            elif (
                self.teacher_id
                and not lecture_teachers(self.subject)
                .filter(pk=self.teacher_id)
                .exists()
            ):
                errors["teacher"] = "Este professor não é do departamento da matéria."
        if errors:
            raise ValidationError(errors)
