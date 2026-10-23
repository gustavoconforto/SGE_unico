from django.db import models

from base.models import TimeStampedModel
from enrollments.models import Enrollment
from grades.models import Subject


class QandA(TimeStampedModel):
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,
        related_name="q_and_as",
        verbose_name="Matrícula",
    )
    q_and_a_date = models.DateField("Data do plantão")
    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name="q_and_as",
        verbose_name="Disciplina",
    )

    class Meta:
        verbose_name = "Plantão"
        verbose_name_plural = "Plantões"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.enrollment.student} - {self.subject}"
