from django.db import models

from base.models import TimeStampedModel
from students.models import Student


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
    student = models.ForeignKey(Student, verbose_name="Aluno", on_delete=models.PROTECT)
    incident_data = models.DateField("Data da ocorrência")

    class Meta:
        verbose_name = "Ocorrência"
        verbose_name_plural = "Ocorrências"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student} - {self.incident_type}"
