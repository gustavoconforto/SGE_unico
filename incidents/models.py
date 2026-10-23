from django.db import models

from base.models import TimeStampedModel
from enrollments.models import Enrollment


class IncidentType(models.Model):
    type = models.CharField("Tipo", max_length=100, unique=True)
    penalty = models.DecimalField("Penalidade", max_digits=4, decimal_places=1)

    class Meta:
        verbose_name = "Tipo de ocorrência"
        verbose_name_plural = "Tipos de ocorrência"
        ordering = ["type"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(penalty__gte=0),
                name="incident_type_penalty_non_negative",
            ),
        ]

    def __str__(self):
        return f"{self.type}"


class Incident(TimeStampedModel):
    incident_type = models.ForeignKey(
        IncidentType, verbose_name="Tipo", on_delete=models.PROTECT
    )
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,
        related_name="incidents",
        verbose_name="Matrícula",
    )
    incident_date = models.DateField("Data da ocorrência")

    class Meta:
        verbose_name = "Ocorrência"
        verbose_name_plural = "Ocorrências"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.enrollment.student} - {self.incident_type}"


class StudentDelayType(models.TextChoices):
    ACCEPTABLE = "A", "Tolerado"
    UNACCEPTABLE = "U", "Não tolerado"


class StudentDelay(TimeStampedModel):
    delay_type = models.CharField(
        "Tipo", max_length=1, choices=StudentDelayType.choices
    )
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,
        related_name="delays",
        verbose_name="Matrícula",
    )
    incident_date = models.DateField("Data da ocorrência")

    class Meta:
        verbose_name = "Atraso"
        verbose_name_plural = "Atrasos"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.enrollment.student} - {self.get_delay_type_display()}"


class BathroomPermission(TimeStampedModel):
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,
        related_name="bathroom_permissions",
        verbose_name="Matrícula",
    )
    class_period = models.SmallIntegerField("Horário")
    incident_date = models.DateField("Data da ocorrência")

    class Meta:
        verbose_name = "Saída para banheiro"
        verbose_name_plural = "Saídas para banheiro"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.enrollment.student} - {self.class_period}º horário"
