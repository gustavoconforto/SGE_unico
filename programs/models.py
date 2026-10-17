from django.db import models


class Program(models.Model):
    name = models.CharField("Nome", max_length=50, unique=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = ["name"]
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"
