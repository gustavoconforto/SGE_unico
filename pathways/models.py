from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from base.models import TimeStampedModel
from employees.models import Employee
from enrollments.models import Enrollment, SchoolYear
from grades.models import SCORE, Bimester

MAX_PATHWAY_SCORE = Decimal("10.00")


class Pathway(models.Model):
    """An extra-curricular course in the catalog, offered again every year."""

    name = models.CharField("Nome", max_length=50, unique=True)
    description = models.TextField("Descrição", blank=True)
    extra_points = models.DecimalField(
        "Pontos extras",
        **SCORE,
        default=Decimal(0),
        validators=[MinValueValidator(0)],
        help_text="Máximo que o itinerário soma à nota extra do bimestre",
    )

    class Meta:
        verbose_name = "Itinerário"
        verbose_name_plural = "Itinerários"
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(extra_points__gte=0),
                name="pathway_extra_points_not_negative",
            ),
        ]

    def __str__(self):
        return f"{self.name}"


class PathwayOffering(TimeStampedModel):
    """A pathway running in a school year; a year can have several groups of
    the same pathway, told apart by `name`."""

    pathway = models.ForeignKey(
        Pathway,
        on_delete=models.PROTECT,
        related_name="offerings",
        verbose_name="Itinerário",
    )
    school_year = models.ForeignKey(
        SchoolYear,
        on_delete=models.PROTECT,
        related_name="pathway_offerings",
        verbose_name="Ano escolar",
    )
    name = models.CharField(
        "Turma", max_length=30, blank=True, help_text="Ex.: Manhã, Grupo A"
    )
    teachers = models.ManyToManyField(
        Employee,
        related_name="pathway_offerings",
        verbose_name="Professores",
        blank=True,
    )
    capacity = models.PositiveSmallIntegerField("Vagas", null=True, blank=True)
    schedule = models.CharField(
        "Horário", max_length=100, blank=True, help_text="Ex.: Terças, 14h às 15h40"
    )

    class Meta:
        verbose_name = "Turma de itinerário"
        verbose_name_plural = "Turmas de itinerário"
        ordering = ["-school_year__begins", "pathway__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["pathway", "school_year", "name"],
                name="unique_pathway_offering_per_year",
            ),
        ]

    def __str__(self):
        label = f"{self.pathway} {self.school_year}"
        return f"{label} - {self.name}" if self.name else label


class PathwayEnrollment(TimeStampedModel):
    """A student's choice of a pathway offering in their school year.

    Leaving sets `left_at` instead of deleting, so past attendance is kept.
    """

    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,
        related_name="pathway_enrollments",
        verbose_name="Matrícula",
    )
    offering = models.ForeignKey(
        PathwayOffering,
        on_delete=models.PROTECT,
        related_name="pathway_enrollments",
        verbose_name="Turma de itinerário",
    )
    joined_at = models.DateField("Data de entrada", default=timezone.localdate)
    left_at = models.DateField("Data de saída", null=True, blank=True)

    class Meta:
        verbose_name = "Inscrição em itinerário"
        verbose_name_plural = "Inscrições em itinerários"
        ordering = ["offering", "enrollment__student__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "offering"],
                name="unique_pathway_enrollment",
            ),
            models.CheckConstraint(
                condition=Q(left_at__isnull=True) | Q(left_at__gte=F("joined_at")),
                name="pathway_enrollment_left_after_joined",
            ),
        ]

    def __str__(self):
        return f"{self.enrollment.student} - {self.offering}"

    def is_member_on(self, day):
        return self.joined_at <= day and (self.left_at is None or day <= self.left_at)

    def clean(self):
        errors = {}
        if self.left_at and self.joined_at and self.left_at < self.joined_at:
            errors["left_at"] = "A saída não pode ser antes da entrada."
        if self.enrollment_id and self.offering_id:
            if (
                self.enrollment.enrollment_type.school_year_id
                != self.offering.school_year_id
            ):
                errors["offering"] = "O itinerário pertence a outro ano escolar."
            elif self.offering.capacity is not None and self.left_at is None:
                taken = (
                    self.offering.pathway_enrollments.filter(left_at__isnull=True)
                    .exclude(pk=self.pk)
                    .count()
                )
                if taken >= self.offering.capacity:
                    errors["offering"] = "Não há vagas nesta turma de itinerário."
        if errors:
            raise ValidationError(errors)


class PathwaySession(TimeStampedModel):
    """A lesson of a pathway offering, created when the teacher takes the roll."""

    offering = models.ForeignKey(
        PathwayOffering,
        on_delete=models.PROTECT,
        related_name="sessions",
        verbose_name="Turma de itinerário",
    )
    date = models.DateField("Data da aula", default=timezone.localdate)
    topic = models.CharField("Conteúdo", max_length=200, blank=True)

    class Meta:
        verbose_name = "Aula de itinerário"
        verbose_name_plural = "Aulas de itinerário"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.offering} - {self.date:%d/%m/%Y}"

    def clean(self):
        if self.offering_id and self.date:
            school_year = self.offering.school_year
            if not school_year.begins <= self.date <= school_year.ends:
                raise ValidationError(
                    {"date": "A data está fora do ano escolar do itinerário."}
                )


class AttendanceStatus(models.TextChoices):
    PRESENT = "P", "Presente"
    ABSENT = "F", "Falta"
    EXCUSED = "J", "Falta justificada"


class PathwayAttendance(models.Model):
    # Attendance is part of its lesson: deleting a lesson deletes its roll call.
    session = models.ForeignKey(
        PathwaySession,
        on_delete=models.CASCADE,
        related_name="attendances",
        verbose_name="Aula",
    )
    pathway_enrollment = models.ForeignKey(
        PathwayEnrollment,
        on_delete=models.PROTECT,
        related_name="attendances",
        verbose_name="Inscrição",
    )
    status = models.CharField(
        "Presença",
        max_length=1,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PRESENT,
    )

    class Meta:
        verbose_name = "Presença em itinerário"
        verbose_name_plural = "Presenças em itinerários"
        ordering = ["session", "pathway_enrollment__enrollment__student__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "pathway_enrollment"],
                name="unique_pathway_attendance",
            ),
        ]

    def __str__(self):
        return f"{self.pathway_enrollment.enrollment.student} - {self.session}: {self.get_status_display()}"

    def clean(self):
        if not (self.session_id and self.pathway_enrollment_id):
            return
        if self.pathway_enrollment.offering_id != self.session.offering_id:
            raise ValidationError(
                {"pathway_enrollment": "O aluno não está inscrito nesta turma."}
            )
        if not self.pathway_enrollment.is_member_on(self.session.date):
            raise ValidationError(
                {"pathway_enrollment": "O aluno não estava inscrito na data da aula."}
            )


class PathwayGrade(TimeStampedModel):
    """The pathway teacher's score for a student in a bimester (0 to 10)."""

    pathway_enrollment = models.ForeignKey(
        PathwayEnrollment,
        on_delete=models.PROTECT,
        related_name="grades",
        verbose_name="Inscrição",
    )
    bimester = models.PositiveSmallIntegerField("Bimestre", choices=Bimester.choices)
    score = models.DecimalField(
        "Nota",
        **SCORE,
        validators=[MinValueValidator(0), MaxValueValidator(MAX_PATHWAY_SCORE)],
    )

    class Meta:
        verbose_name = "Nota de itinerário"
        verbose_name_plural = "Notas de itinerário"
        ordering = ["pathway_enrollment", "bimester"]
        constraints = [
            models.UniqueConstraint(
                fields=["pathway_enrollment", "bimester"],
                name="unique_pathway_grade_per_bimester",
            ),
            models.CheckConstraint(
                condition=Q(score__gte=0, score__lte=MAX_PATHWAY_SCORE),
                name="pathway_grade_score_range",
            ),
            models.CheckConstraint(
                condition=Q(bimester__gte=1, bimester__lte=4),
                name="pathway_grade_bimester_range",
            ),
        ]

    def __str__(self):
        return f"{self.pathway_enrollment} - {self.bimester}º bim.: {self.score}"


class ExtraGradeSettings(models.Model):
    """Rules of the extra grade ("nota extra") of a school year.

    Changes only affect the next calculations; bimesters already calculated
    keep their grades until they are calculated again.
    """

    school_year = models.OneToOneField(
        SchoolYear,
        on_delete=models.PROTECT,
        related_name="extra_grade_settings",
        verbose_name="Ano escolar",
    )
    min_pathway_attendance = models.DecimalField(
        "Frequência mínima nos itinerários (%)",
        max_digits=5,
        decimal_places=2,
        default=Decimal(75),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Abaixo dela o itinerário não soma pontos no bimestre",
    )
    q_and_a_min_sessions = models.PositiveSmallIntegerField(
        "Mínimo de plantões no bimestre",
        default=3,
        validators=[MinValueValidator(1)],
    )
    q_and_a_points = models.DecimalField(
        "Pontos pelos plantões",
        **SCORE,
        default=Decimal("0.50"),
        validators=[MinValueValidator(0)],
        help_text="Somados à nota extra de quem atinge o mínimo de plantões",
    )

    class Meta:
        verbose_name = "Configuração da nota extra"
        verbose_name_plural = "Configurações da nota extra"
        ordering = ["-school_year__begins"]
        constraints = [
            models.CheckConstraint(
                condition=Q(min_pathway_attendance__gte=0)
                & Q(min_pathway_attendance__lte=100),
                name="extra_grade_settings_attendance_range",
            ),
            models.CheckConstraint(
                condition=Q(q_and_a_min_sessions__gte=1),
                name="extra_grade_settings_min_sessions_positive",
            ),
            models.CheckConstraint(
                condition=Q(q_and_a_points__gte=0),
                name="extra_grade_settings_points_not_negative",
            ),
        ]

    def __str__(self):
        return f"Nota extra {self.school_year}"

    @classmethod
    def for_school_year(cls, school_year):
        """The year's settings, created with the defaults on first use."""
        return cls.objects.get_or_create(school_year=school_year)[0]
