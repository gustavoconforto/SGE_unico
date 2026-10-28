from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from base.models import TimeStampedModel
from classes.models import Class
from programs.models import Program
from students.models import Student


class SchoolYear(models.Model):
    begins = models.DateField("Data de início")
    ends = models.DateField("Data de fim")
    bi_1_begins = models.DateField(
        "Data de início do 1 Bimestre", blank=True, null=True
    )
    bi_1_ends = models.DateField("Data de fim do 1 Bimestre", blank=True, null=True)
    bi_2_begins = models.DateField(
        "Data de início do 2 Bimestre", blank=True, null=True
    )
    bi_2_ends = models.DateField("Data de fim do 2 Bimestre", blank=True, null=True)
    bi_3_begins = models.DateField(
        "Data de início do 3 Bimestre", blank=True, null=True
    )
    bi_3_ends = models.DateField("Data de fim do 3 Bimestre", blank=True, null=True)
    bi_4_begins = models.DateField(
        "Data de início do 4 Bimestre", blank=True, null=True
    )
    bi_4_ends = models.DateField("Data de fim do 4 Bimestre", blank=True, null=True)
    # Required by SchoolYearForm; nullable only for years created before them.
    school_days = models.PositiveSmallIntegerField(
        "Dias letivos",
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Total de dias letivos do ano",
    )
    total_hours = models.PositiveIntegerField(
        "Carga horária (horas)",
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Total de horas oferecidas ao aluno no ano, base da frequência",
    )

    def __str__(self):
        return f"{self.begins.year}"

    class Meta:
        verbose_name = "Ano escolar"
        verbose_name_plural = "Anos escolares"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(school_days__isnull=True)
                | models.Q(school_days__gte=1),
                name="school_year_school_days_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(total_hours__isnull=True)
                | models.Q(total_hours__gte=1),
                name="school_year_total_hours_positive",
            ),
        ]


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
    punctuality_discount = models.DecimalField(
        "Desconto de pontualidade",
        max_digits=10,
        decimal_places=2,
        default=Decimal("90.00"),
        help_text="Abatido de cada parcela paga por boleto até o vencimento",
    )
    description = models.TextField("Descrição", blank=True)
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


class DiscountGroup(models.TextChoices):
    """Which installments a discount applies to. The first installment is
    1/12 of the contract; the remaining 11/12 are split over the other months.
    """

    FIRST = "F", "1ª parcela"
    REMAINING = "R", "Demais parcelas"


def percent_of(value, percent):
    return (value * percent / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)


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
    gross_value = models.DecimalField(
        "Valor bruto do contrato",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Preenchido automáticamente",
    )
    first_discount_percent = models.DecimalField(
        "Desconto da 1ª parcela (%)",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Preenchido automáticamente",
    )
    remaining_discount_percent = models.DecimalField(
        "Desconto das demais parcelas (%)",
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
    def first_gross_value(self):
        """1/12 of the contract, charged in the first installment."""
        return (self.gross_value / 12).quantize(Decimal("0.01"), ROUND_HALF_UP)

    @property
    def remaining_gross_value(self):
        return self.gross_value - self.first_gross_value

    @property
    def first_discount_value(self):
        return percent_of(self.first_gross_value, self.first_discount_percent)

    @property
    def remaining_discount_value(self):
        return percent_of(self.remaining_gross_value, self.remaining_discount_percent)

    @property
    def first_net_value(self):
        return self.first_gross_value - self.first_discount_value

    @property
    def remaining_net_value(self):
        return self.remaining_gross_value - self.remaining_discount_value

    @property
    def discount_value(self):
        return self.first_discount_value + self.remaining_discount_value

    @property
    def net_value(self):
        return self.gross_value - self.discount_value

    @property
    def overall_discount_percent(self):
        """Discount over the whole contract, both groups combined."""
        if not self.gross_value:
            return Decimal(0)
        return (self.discount_value * 100 / self.gross_value).quantize(
            Decimal("0.01"), ROUND_HALF_UP
        )

    def fill_contract_values(self):
        if self.gross_value is None and self.enrollment_type_id:
            self.gross_value = self.enrollment_type.total_price
        if self.first_discount_percent is None:
            self.first_discount_percent = Decimal(0)
        if self.remaining_discount_percent is None:
            self.remaining_discount_percent = Decimal(0)

    def save(self, *args, **kwargs):
        self.fill_contract_values()
        super().save(*args, **kwargs)

    @transaction.atomic
    def save_with_discounts(self, discounts):
        """Create the enrollment with these unsaved EnrollmentDiscount rows.

        Each group's percentage is the sum of its discounts and must be set
        before the first save: the post_save signal creates the account from
        them.
        """
        for discount in discounts:
            if discount.percentage is None:
                discount.percentage = discount.discount_type.percentage
        self.first_discount_percent = sum(
            (d.percentage for d in discounts if d.group == DiscountGroup.FIRST),
            Decimal(0),
        )
        self.remaining_discount_percent = sum(
            (d.percentage for d in discounts if d.group == DiscountGroup.REMAINING),
            Decimal(0),
        )
        self.save()
        for discount in discounts:
            discount.enrollment = self
        EnrollmentDiscount.objects.bulk_create(discounts)

    def sync_documents(self):
        """Create the documents for any NeededDocumentType this enrollment lacks."""
        existing = self.documents.values_list("type_id", flat=True)
        missing = NeededDocumentType.objects.exclude(pk__in=existing)
        return EnrollmentNeededDocument.objects.bulk_create(
            EnrollmentNeededDocument(enrollment=self, type=doc_type)
            for doc_type in missing
        )

    def clean(self):
        errors = {}
        if (
            self.student_id
            and not self.student.guardian_links.filter(is_financial=True).exists()
        ):
            errors["student"] = (
                "O aluno precisa ter ao menos um responsável financeiro cadastrado."
            )
        if self.school_class_id and self.enrollment_type_id:
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


class EnrollmentDiscount(TimeStampedModel):
    """One discount of an enrollment: a DiscountType or a custom percentage.

    It applies to the first installment or to the remaining ones (group);
    the same type can be in both groups. The percentage is copied from the
    type, so later changes to it don't affect existing contracts. A custom
    discount (no type) needs an observation explaining who allowed it.
    """

    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,
        related_name="discounts",
        verbose_name="Matrícula",
    )
    discount_type = models.ForeignKey(
        DiscountType,
        on_delete=models.PROTECT,
        related_name="enrollment_discounts",
        verbose_name="Tipo de desconto",
        null=True,
        blank=True,
    )
    group = models.CharField("Parcelas", max_length=1, choices=DiscountGroup.choices)
    percentage = models.DecimalField(
        "Percentual",
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    observation = models.CharField("Observação", max_length=200, blank=True)

    def __str__(self):
        label = self.discount_type or "Desconto avulso"
        return f"{label} ({self.percentage}%, {self.get_group_display()})"

    class Meta:
        verbose_name = "Desconto da matrícula"
        verbose_name_plural = "Descontos da matrícula"
        ordering = ["enrollment", "group", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "group", "discount_type"],
                name="unique_enrollment_discount_type",
            ),
            models.CheckConstraint(
                condition=models.Q(group__in=DiscountGroup.values),
                name="enrollment_discount_group_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(percentage__gte=0, percentage__lte=100),
                name="enrollment_discount_percentage_range",
            ),
            models.CheckConstraint(
                condition=models.Q(discount_type__isnull=False)
                | ~models.Q(observation=""),
                name="custom_enrollment_discount_has_observation",
            ),
        ]


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
