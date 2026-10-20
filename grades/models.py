from django.db import models

# Create your models here.


class Subject(models.Model):
    name = models.CharField("nome", max_length=50, unique=True)

    class Meta:
        verbose_name = "Matéria"
        verbose_name_plural = "Matérias"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}"
