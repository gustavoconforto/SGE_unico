from django.db import models

from employees.models import Employee


class Department(models.Model):
    """A group of subjects and the teachers who can teach them."""

    name = models.CharField("Nome", max_length=50, unique=True)
    teachers = models.ManyToManyField(
        Employee,
        related_name="departments",
        verbose_name="Professores",
        blank=True,
    )

    class Meta:
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}"
