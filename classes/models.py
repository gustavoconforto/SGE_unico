from django.db import models
from django.db.models import PROTECT

from programs.models import Program


class Shift(models.TextChoices):
    MORNING = "M", "Manhã"
    AFTERNOON = "T", "Tarde"
    EVENING = "N", "Noite"
    FULL_TIME = "I", "Integral"


class Class(models.Model):
    program = models.ForeignKey(
        Program, on_delete=models.PROTECT, related_name="classes", verbose_name="Curso"
    )
    year = models.ForeignKey(
        "enrollments.SchoolYear",
        on_delete=PROTECT,
        related_name="classes",
        verbose_name="Ano letivo",
    )
    grade_level = models.PositiveSmallIntegerField("Série", null=True, blank=True)
    name = models.CharField("Nome", max_length=30)
    shift = models.CharField("Turno", max_length=1, choices=Shift.choices, blank=True)
    capacity = models.PositiveSmallIntegerField("Vagas", null=True, blank=True)

    def __str__(self):
        level = f"{self.grade_level}° " if self.grade_level else ""
        return f"{level}{self.name} - {self.year}"

    class Meta:
        ordering = ["-year", "program", "grade_level", "name"]
        verbose_name = "Turma"
        verbose_name_plural = "Turmas"
        constraints = [
            models.UniqueConstraint(
                fields=["year", "program", "name"], name="unique_class_per_year_program"
            ),
        ]
