from django.contrib.auth.hashers import identify_hasher, make_password
from django.db import models

from base.models import Person


class EmployeeRoleType(models.Model):
    role = models.CharField("Cargo", max_length=20)

    def __str__(self):
        return f"{self.role}"

    class Meta:
        verbose_name = "Cargo"
        verbose_name_plural = "Cargos"
        ordering = ["role"]

class Employee(Person):
    role = models.ForeignKey(EmployeeRoleType, on_delete=models.PROTECT, verbose_name="Cargo", related_name="funcionarios")
    can_access_suga = models.BooleanField("Pode acessar o SUGA", default=False)
    password_suga = models.CharField(verbose_name="Senha Suga", max_length=128, blank=True)

    def save(self, *args, **kwargs):
        if self.password_suga and not self._is_hashed(self.password_suga):
            self.password_suga = make_password(self.password_suga)
        super().save(*args, **kwargs)

    @staticmethod
    def _is_hashed(value):
        try:
            identify_hasher(value)
        except ValueError:
            return False
        return True

    class Meta(Person.Meta):
        verbose_name = "Funcionário"
        verbose_name_plural = "Funcionários"
