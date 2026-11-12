from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from base.models import TimeStampedModel
from employees.models import Employee
from enrollments.models import Enrollment, SchoolYear
from grades.models import SCORE, Bimester
from lessons.models import Weekday


class WorkloadType(models.TextChoices):
    NONE = "N", "Sem carga horária"
    FIXED = "F", "Fixa"
    ATTENDANCE = "P", "Por presença"


class Pathway(models.Model):
    """An extra-curricular course in the catalog, offered again every year."""

    name = models.CharField("Nome", max_length=50, unique=True)
    description = models.TextField("Descrição", blank=True)
    extra_points = models.DecimalField(
        "Nota máxima",
        **SCORE,
        default=Decimal(0),
        validators=[MinValueValidator(0)],
        help_text="Maior nota que o professor pode dar no bimestre; "
        "deixe 0 se o itinerário não dá nota extra",
    )
    workload_type = models.CharField(
        "Carga horária",
        max_length=1,
        choices=WorkloadType.choices,
        default=WorkloadType.NONE,
        help_text="Por presença: cada aula assistida vale 45 minutos",
    )
    workload_hours = models.DecimalField(
        "Horas no ano",
        max_digits=6,
        decimal_places=2,
        default=Decimal(0),
        validators=[MinValueValidator(0)],
        help_text="Só para carga horária fixa",
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
            models.CheckConstraint(
                condition=Q(workload_type=WorkloadType.FIXED, workload_hours__gt=0)
                | (~Q(workload_type=WorkloadType.FIXED) & Q(workload_hours=0)),
                name="pathway_workload_hours_only_when_fixed",
            ),
        ]

    def __str__(self):
        return f"{self.name}"

    @property
    def gives_grade(self):
        return self.extra_points > 0

    def clean(self):
        if self.workload_type != WorkloadType.FIXED:
            self.workload_hours = Decimal(0)
        elif not self.workload_hours:
            raise ValidationError(
                {"workload_hours": "Informe as horas da carga horária fixa."}
            )


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
    weekdays = models.JSONField(
        "Dias de aula",
        default=list,
        blank=True,
        help_text="Dias da semana em que há aula; montam as datas do diário",
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

    def clean(self):
        weekdays = self.weekdays
        if not isinstance(weekdays, list) or not set(weekdays) <= set(Weekday.values):
            raise ValidationError({"weekdays": "Escolha dias de segunda a sábado."})
        self.weekdays = sorted(set(weekdays))


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
    """The points the pathway teacher gives a student in a bimester, added as
    they are to the extra grade; at most the pathway's `extra_points`."""

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
        validators=[MinValueValidator(0)],
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
                condition=Q(score__gte=0),
                name="pathway_grade_score_not_negative",
            ),
            models.CheckConstraint(
                condition=Q(bimester__gte=1, bimester__lte=4),
                name="pathway_grade_bimester_range",
            ),
        ]

    def __str__(self):
        return f"{self.pathway_enrollment} - {self.bimester}º bim.: {self.score}"

    def clean(self):
        if not self.pathway_enrollment_id or self.score is None:
            return
        pathway = self.pathway_enrollment.offering.pathway
        if not pathway.gives_grade:
            raise ValidationError("Este itinerário não dá nota extra.")
        if self.score > pathway.extra_points:
            raise ValidationError(
                {"score": f"A nota máxima deste itinerário é {pathway.extra_points}."}
            )
