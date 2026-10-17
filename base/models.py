from django.db import models
from django.db.models import Q


class SexType(models.TextChoices):
    MALE = "M", "Masculino"
    FEMALE = "F", "Feminino"


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        abstract = True


class Person(TimeStampedModel):
    """Personal, document, contact and address fields shared by people records."""

    name = models.CharField("Nome civil", max_length=200)
    sex = models.CharField(
        "Sexo", max_length=1, choices=SexType.choices, blank=True, help_text="M ou F"
    )
    cpf = models.CharField(
        "CPF", max_length=11, blank=False, help_text="Sem ponto nem -", unique=True
    )
    rg = models.CharField(
        "RG", max_length=20, blank=False, help_text="Sem ponto nem -", unique=True
    )
    issuing_authority = models.CharField(
        "Órgão expedidor",
        max_length=20,
        blank=False,
        help_text="Pode inserir ponto nem -",
    )
    birth_date = models.DateField("Data de nascimento", null=True, blank=True)
    nationality = models.CharField("Nacionalidade", max_length=50, blank=True)
    place_of_birth = models.CharField("Naturalidade", max_length=50, blank=True)
    phone = models.CharField(
        "Telefone", max_length=20, blank=True, help_text="(00) 0000-0000"
    )
    mobile = models.CharField(
        "Celular", max_length=20, blank=True, help_text="(00) 0000-0000"
    )
    email = models.EmailField("Email", blank=True)
    address = models.CharField(
        "Endereço", max_length=200, blank=True, help_text="Pode usar ponto e -"
    )
    neighborhood = models.CharField("Bairro", max_length=100, blank=True)
    city = models.CharField("Cidade", max_length=100, blank=True)
    state = models.CharField("UF", max_length=2, blank=True)
    zip_code = models.CharField(
        "CEP", max_length=8, blank=True, help_text="Sem hífen (-)"
    )

    class Meta:
        abstract = True
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["cpf"],
                condition=~Q(cpf=""),
                name="%(app_label)s_%(class)s_unique_cpf",
            ),
        ]

    def __str__(self):
        return f"{self.name}"
