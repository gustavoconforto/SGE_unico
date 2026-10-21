from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from base.models import TimeStampedModel
from departments.models import Department
from employees.models import Employee
from enrollments.models import Enrollment

SCORE = {"max_digits": 4, "decimal_places": 2}


class Subject(models.Model):
    name = models.CharField("nome", max_length=50, unique=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="subjects",
        verbose_name="Departamento",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Matéria"
        verbose_name_plural = "Matérias"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}"


class Bimester(models.IntegerChoices):
    FIRST = 1, "1º bimestre"
    SECOND = 2, "2º bimestre"
    THIRD = 3, "3º bimestre"
    FOURTH = 4, "4º bimestre"


# Recovery grades are stored in a fifth period: the recovery exam is taken once
# the year is over, by students whose annual average is below the passing grade.
FINAL_RECOVERY = 5
GRADE_PERIODS = [*Bimester.choices, (FINAL_RECOVERY, "Recuperação final")]


class ExamKind(models.TextChoices):
    REGULAR = "R", "Avaliação"
    BONUS = "B", "Ponto extra"
    RECOVERY = "C", "Recuperação"


class ExamType(models.Model):
    """An evaluation applied every bimester (P1, prova bimestral, recuperação...).

    Each exam's maximum already sets its share of the bimester (PS up to 3,
    PB up to 6...): regular and bonus scores are added up, capped at 10. A
    recovery exam is the final recovery: its grades go in the FINAL_RECOVERY
    period, never in a bimester.
    """

    name = models.CharField("Nome", max_length=50, unique=True)
    code = models.CharField("Sigla", max_length=5, unique=True)
    kind = models.CharField(
        "Tipo", max_length=1, choices=ExamKind.choices, default=ExamKind.REGULAR
    )
    max_score = models.DecimalField("Nota máxima", **SCORE, default=Decimal("10.00"))
    order = models.PositiveSmallIntegerField(
        "Ordem", default=0, help_text="Posição da coluna no boletim"
    )

    class Meta:
        verbose_name = "Tipo de avaliação"
        verbose_name_plural = "Tipos de avaliação"
        ordering = ["order", "name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(max_score__gt=0), name="exam_type_max_score_positive"
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class GradeLevel(models.IntegerChoices):
    FIRST = 1, "1ª série"
    SECOND = 2, "2ª série"
    THIRD = 3, "3ª série"


class GradeLevelSubject(models.Model):
    """A subject taught in every class of a series (`Class.grade_level`).

    The report card's rows come from here. A subject can have several teachers.
    """

    grade_level = models.PositiveSmallIntegerField("Série", choices=GradeLevel.choices)
    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name="grade_level_subjects",
        verbose_name="Matéria",
    )
    teachers = models.ManyToManyField(
        Employee,
        related_name="grade_level_subjects",
        verbose_name="Professores",
        blank=True,
    )
    weekly_classes = models.DecimalField(
        "Aulas por semana",
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Média semanal; aceita frações (ex.: 1,5)",
    )

    class Meta:
        verbose_name = "Matéria da série"
        verbose_name_plural = "Matérias da série"
        ordering = ["grade_level", "subject__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["grade_level", "subject"],
                name="unique_subject_per_grade_level",
            ),
            models.CheckConstraint(
                condition=Q(weekly_classes__gte=0),
                name="grade_level_subject_weekly_classes_not_negative",
            ),
            models.CheckConstraint(
                condition=Q(grade_level__gte=1, grade_level__lte=3),
                name="grade_level_subject_level_range",
            ),
        ]

    def __str__(self):
        return f"{self.subject} - {self.get_grade_level_display()}"


class Grade(TimeStampedModel):
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,
        related_name="grades",
        verbose_name="Matrícula",
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name="grades", verbose_name="Matéria"
    )
    exam_type = models.ForeignKey(
        ExamType,
        on_delete=models.PROTECT,
        related_name="grades",
        verbose_name="Avaliação",
    )
    bimester = models.PositiveSmallIntegerField("Bimestre", choices=GRADE_PERIODS)
    score = models.DecimalField("Nota", **SCORE, validators=[MinValueValidator(0)])

    class Meta:
        verbose_name = "Nota"
        verbose_name_plural = "Notas"
        ordering = ["enrollment", "subject", "bimester", "exam_type"]
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "subject", "exam_type", "bimester"],
                name="unique_grade_per_exam",
            ),
            models.CheckConstraint(
                condition=Q(score__gte=0), name="grade_score_not_negative"
            ),
            models.CheckConstraint(
                condition=Q(bimester__gte=1, bimester__lte=FINAL_RECOVERY),
                name="grade_bimester_range",
            ),
        ]

    def __str__(self):
        return f"{self.enrollment.student} - {self.subject} - {self.bimester}º bim. - {self.exam_type.code}: {self.score}"

    def clean(self):
        if (
            self.exam_type_id
            and self.score is not None
            and self.score > self.exam_type.max_score
        ):
            raise ValidationError(
                {
                    "score": f"A nota máxima desta avaliação é {self.exam_type.max_score}."
                }
            )
        if self.exam_type_id and self.bimester is not None:
            is_recovery = self.exam_type.kind == ExamKind.RECOVERY
            if is_recovery != (self.bimester == FINAL_RECOVERY):
                raise ValidationError(
                    {
                        "bimester": "A recuperação é lançada só na recuperação final."
                        if is_recovery
                        else "Na recuperação final só se lançam notas de recuperação."
                    }
                )
        if self.enrollment_id and self.subject_id:
            school_class = self.enrollment.school_class
            if not GradeLevelSubject.objects.filter(
                grade_level=school_class.grade_level if school_class else None,
                subject_id=self.subject_id,
            ).exists():
                raise ValidationError(
                    {"subject": "Esta matéria não é oferecida na série do aluno."}
                )
