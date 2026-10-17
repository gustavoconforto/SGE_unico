from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from base.models import TimeStampedModel
from classes.models import Class
from programs.models import Program
from students.models import Student


class SchoolYear(models.Model):
    begins = models.DateField("Data de início")
    ends = models.DateField("Data de fim")
    bi_1_begins = models.DateField("Data de início do 1 Bimestre")
    bi_1_ends = models.DateField("Data de fim do 1 Bimestre")
    bi_2_begins = models.DateField("Data de início do 2 Bimestre")
    bi_2_ends = models.DateField("Data de fim do 2 Bimestre")
    bi_3_begins = models.DateField("Data de início do 3 Bimestre")
    bi_3_ends = models.DateField("Data de fim do 3 Bimestre")
    bi_4_begins = models.DateField("Data de início do 4 Bimestre")
    bi_4_ends = models.DateField("Data de fim do 4 Bimestre")

    def __str__(self):
        return f"{self.begins.year}"

    class Meta:
        verbose_name = "Ano escolar"
        verbose_name_plural = "Anos escolares"


class NeededDocumentType(models.Model):
    description = models.CharField("Descrição", max_length=50)

    def __str__(self):
        return f"{self.description}"

    class Meta:
        verbose_name = "Documento Necessário"
        verbose_name_plural = "Documentos Necessários"


class EnrollmentStatus(models.TextChoices):
    ACTIVE = "A", "Ativa"
    TRANSFERRED = "T", "Transferida"
    DROPPED = "D", "Desistente"
    COMPLETED = "C", "Concluída"
    CANCELLED = "X", "Cancelada"


class LevelTypes(models.TextChoices):
    GRADE_1 = "1", "1ª Série"
    GRADE_2 = "2", "2ª Série"
    GRADE_3 = "3", "3ª Série"


class EnrollmentType(models.Model):
    program = models.ForeignKey(
        Program,
        on_delete=models.PROTECT,
        related_name="enrollments",
        verbose_name="Curso",
    )
    level = models.CharField(
        "Série", choices=LevelTypes, max_length=1, null=False, blank=True
    )
    start_date = models.DateField(
        "Início do contrato", blank=True, help_text="Preenchido automaticamente"
    )
    end_date = models.DateField(
        "Fim do contrato", blank=True, help_text="Preenchido automaticamente"
    )
    total_price = models.DecimalField("Valor total", max_digits=10, decimal_places=2)
    description = models.TextField("Descrição")
    school_year = models.ForeignKey(
        SchoolYear,
        on_delete=models.PROTECT,
        related_name="enrollments",
        verbose_name="Ano escolar",
    )

    def __str__(self):
        return f"{self.program} - {self.get_level_display()} - {self.school_year.begins.year}"

    def save(self, *args, **kwargs):
        if self.start_date is None:
            self.start_date = self.school_year.begins
        if self.end_date is None:
            self.end_date = self.school_year.ends
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Tipo de contrato"
        verbose_name_plural = "Tipos de contrato"
        ordering = ["-school_year__begins", "program", "level"]


class DiscountType(models.Model):
    description = models.CharField("Descrição", max_length=200)
    percentage = models.DecimalField(
        "Percentual",
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Entre 0 e 100",
    )

    def __str__(self):
        return f"{self.description}"

    class Meta:
        verbose_name = "Tipo de desconto"
        verbose_name_plural = "Tipos de desconto"
        ordering = ["description"]


class Enrollment(TimeStampedModel):
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="enrollments",
        verbose_name="Aluno",
    )
    enrollment_type = models.ForeignKey(
        EnrollmentType,
        on_delete=models.PROTECT,
        related_name="enrollments",
        verbose_name="Tipo de contrato",
    )
    school_class = models.ForeignKey(
        Class,
        on_delete=models.PROTECT,
        related_name="enrollments",
        verbose_name="Turma",
        null=True,
        blank=True,
    )
    status = models.CharField(
        "Situação",
        max_length=1,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ACTIVE,
    )
    enrolled_at = models.DateField(
        "Data da matrícula",
        default=timezone.localdate,
        help_text="Preenchido automáticamente",
        blank=True,
    )
    discount = models.ForeignKey(
        DiscountType,
        on_delete=models.PROTECT,
        verbose_name="Desconto",
        related_name="enrollments",
        blank=True,
        null=True,
    )

    gross_value = models.DecimalField(
        "Valor bruto do contrato",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Preenchido automáticamente",
    )
    discount_percent = models.DecimalField(
        "Percentual de desconto",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Preenchido automáticamente",
    )
    installments_count = models.PositiveSmallIntegerField(
        "Número de parcelas",
        default=12,
        validators=[MinValueValidator(1), MaxValueValidator(24)],
        help_text="Preenchido automáticamente",
        blank=True,
    )
    due_day = models.PositiveSmallIntegerField(
        "Dia de vencimento",
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(28)],
        help_text="Até 28, para existir em todos os meses",
    )

    def __str__(self):
        return f"{self.student} - {self.enrollment_type}"

    @property
    def discount_value(self):
        return (self.gross_value * self.discount_percent / 100).quantize(
            Decimal("0.01"), ROUND_HALF_UP
        )

    @property
    def net_value(self):
        return self.gross_value - self.discount_value

    def fill_contract_values(self):
        if self.gross_value is None and self.enrollment_type_id:
            self.gross_value = self.enrollment_type.total_price
        if self.discount_percent is None:
            self.discount_percent = (
                self.discount.percentage if self.discount_id else Decimal(0)
            )

    def save(self, *args, **kwargs):
        self.fill_contract_values()
        super().save(*args, **kwargs)

    def sync_documents(self):
        """Create the documents for any NeededDocumentType this enrollment lacks."""
        existing = self.documents.values_list("type_id", flat=True)
        missing = NeededDocumentType.objects.exclude(pk__in=existing)
        return EnrollmentNeededDocument.objects.bulk_create(
            EnrollmentNeededDocument(enrollment=self, type=doc_type)
            for doc_type in missing
        )

    def clean(self):
        if self.school_class_id is None or self.enrollment_type_id is None:
            return
        errors = {}
        if self.school_class.year_id != self.enrollment_type.school_year_id:
            errors["school_class"] = "A turma pertence a outro ano letivo."
        elif self.school_class.program_id != self.enrollment_type.program_id:
            errors["school_class"] = "A turma pertence a outro curso."
        elif self.enrollment_type.level and self.school_class.grade_level != int(
            self.enrollment_type.level
        ):
            errors["school_class"] = "A turma pertence a outra série."
        if errors:
            raise ValidationError(errors)

    class Meta:
        ordering = ["-enrollment_type__school_year__begins", "student__name"]
        unique_together = ["student", "enrollment_type"]
        verbose_name = "Matrícula"
        verbose_name_plural = "Matrículas"


class EnrollmentNeededDocument(TimeStampedModel):
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,
        verbose_name="Contrato",
        related_name="documents",
    )
    type = models.ForeignKey(
        NeededDocumentType,
        on_delete=models.PROTECT,
        verbose_name="Tipo",
        related_name="documents",
    )
    is_delivered = models.BooleanField(default=False, verbose_name="Entregue")

    def __str__(self):
        return f"{self.type}"

    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
