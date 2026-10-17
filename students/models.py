from datetime import date
from pathlib import Path

from django.db import models
from django.templatetags.static import static

from base.models import Person

STUDENT_PHOTO_PLACEHOLDER = "img/student-placeholder.svg"
STUDENT_PHOTO_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


def student_photo_path(instance, filename):
    name = f"students/{instance.registration}{Path(filename).suffix.lower()}"
    storage = instance._meta.get_field("photo").storage
    if storage.exists(name):
        storage.delete(name)
    return name


class MaritalStatus(models.TextChoices):
    SINGLE = "S", "Solteiro(a)"
    MARRIED = "C", "Casado(a)"
    STABLE_UNION = "U", "União estável"
    DIVORCED = "D", "Divorciado(a)"
    WIDOWED = "V", "Viúvo(a)"


class Relationship(models.TextChoices):
    FATHER = "PAI", "Pai"
    MOTHER = "MAE", "Mãe"
    GRANDPARENT = "AVO", "Avô/Avó"
    UNCLE_AUNT = "TIO", "Tio(a)"
    SIBLING = "IRM", "Irmão(ã)"
    STEPPARENT = "PAD", "Padrasto/Madrasta"
    LEGAL_GUARDIAN = "TUT", "Tutor(a) legal"
    OTHER = "OUT", "Outro"


class Guardian(Person):
    marital_status = models.CharField(
        "Estado civil", max_length=1, choices=MaritalStatus.choices, blank=True
    )

    class Meta(Person.Meta):
        verbose_name = "Responsável"
        verbose_name_plural = "Responsáveis"


class Student(Person):
    social_name = models.CharField("Nome social", max_length=200, blank=True)
    use_social_name = models.BooleanField("Usar Nome social", default=False)
    registration = models.CharField(
        "Matrícula",
        max_length=20,
        unique=True,
        help_text="Gerado automaticamente",
        blank=True,
        null=False,
    )
    photo = models.ImageField("Foto", upload_to=student_photo_path, blank=True)

    guardians = models.ManyToManyField(
        Guardian,
        through="GuardianAssociation",
        related_name="students",
        verbose_name="Responsáveis",
    )

    class Meta(Person.Meta):
        verbose_name = "Aluno"
        verbose_name_plural = "Alunos"

    def save(self, *args, **kwargs):
        if not self.registration:
            self.registration = self._next_registration()
        if self.pk:
            old_photo = (
                Student.objects.filter(pk=self.pk)
                .values_list("photo", flat=True)
                .first()
            )
            if old_photo and old_photo != self.photo.name:
                self.photo.storage.delete(old_photo)
        super().save(*args, **kwargs)

    @staticmethod
    def _next_registration():
        prefix = str(date.today().year)
        last = (
            Student.objects.filter(
                registration__startswith=prefix,
                registration__regex=rf"^{prefix}\d{{5}}$",
            )
            .order_by("-registration")
            .values_list("registration", flat=True)
            .first()
        )
        seq = int(last[len(prefix) :]) + 1 if last else 1
        return f"{prefix}{seq:05d}"

    @property
    def photo_url(self):
        if self.photo:
            return self.photo.url
        # Fallback for photos copied directly to media/students/<registration>.<ext>
        storage = self.photo.storage
        for ext in STUDENT_PHOTO_EXTENSIONS:
            name = f"students/{self.registration}{ext}"
            if storage.exists(name):
                return storage.url(name)
        return static(STUDENT_PHOTO_PLACEHOLDER)

    def __str__(self):
        if self.use_social_name and self.social_name:
            return f"{self.social_name}"
        return f"{self.name}"


class GuardianAssociation(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="guardian_links",
        verbose_name="Aluno",
    )
    guardian = models.ForeignKey(
        Guardian,
        on_delete=models.PROTECT,
        related_name="student_links",
        verbose_name="Responsável",
    )
    relationship = models.CharField(
        "Parentesco", max_length=3, choices=Relationship.choices
    )
    is_financial = models.BooleanField("Responsável financeiro", default=False)
    is_primary_contact = models.BooleanField("Contato principal", default=False)
    living_with = models.BooleanField("Mora com o aluno(a)", default=False)
    pick_up = models.BooleanField("Autorizado a buscar o aluno", default=False)

    class Meta:
        verbose_name = "Responsável"
        verbose_name_plural = "Responsáveis"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "guardian"], name="unique_student_guardian"
            ),
        ]

    def __str__(self):
        return f"{self.guardian} ({self.get_relationship_display()}) - {self.student}"
