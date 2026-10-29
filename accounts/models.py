from decimal import Decimal

from django.db import models
from django.db.models import (
    Case,
    Count,
    DecimalField,
    F,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Greatest
from django.utils import timezone

from base.models import TimeStampedModel
from enrollments.models import Enrollment
from students.models import Guardian, Student

MONEY = {"max_digits": 10, "decimal_places": 2}
ZERO = Decimal("0.00")


class Direction(models.TextChoices):
    RECEIVABLE = "R", "A receber"
    PAYABLE = "P", "A pagar"


class AccountType(models.Model):
    name = models.CharField("Nome", max_length=100, unique=True)
    direction = models.CharField("Natureza", max_length=1, choices=Direction.choices)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Categoria financeira"
        verbose_name_plural = "Categorias financeiras"
        ordering = ["direction", "name"]


class Supplier(TimeStampedModel):
    name = models.CharField("Nome", max_length=200)
    document = models.CharField(
        "CPF/CNPJ", max_length=14, blank=True, help_text="Somente números"
    )
    phone = models.CharField("Telefone", max_length=20, blank=True)
    email = models.EmailField("Email", blank=True)
    notes = models.TextField("Observações", blank=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Fornecedor"
        verbose_name_plural = "Fornecedores"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["document"],
                condition=~Q(document=""),
                name="unique_supplier_document",
            ),
        ]


class AccountQuerySet(models.QuerySet):
    def with_installment_summary(self):
        """Annotate counts used to derive the account situation without N+1 queries."""
        pending = Q(installments__status__in=PENDING_STATUSES)
        return self.annotate(
            installments_total=Count("installments"),
            installments_pending=Count("installments", filter=pending),
            installments_overdue=Count(
                "installments",
                filter=pending & Q(installments__due_date__lt=timezone.localdate()),
            ),
            installments_paid=Count(
                "installments", filter=Q(installments__status=InstallmentStatus.PAID)
            ),
        )

    def with_payment_dates(self):
        """Annotate the due date still owed (or the last one) and the last payment.

        Subqueries rather than joins, so the counts above aren't multiplied.
        """
        installments = Installment.objects.filter(account=OuterRef("pk"))
        next_due = installments.filter(status__in=PENDING_STATUSES).order_by("due_date")
        last_due = installments.order_by("-due_date")
        last_payment = Payment.objects.filter(
            installment__account=OuterRef("pk")
        ).order_by("-paid_at")
        return self.annotate(
            due_date=Coalesce(
                Subquery(next_due.values("due_date")[:1]),
                Subquery(last_due.values("due_date")[:1]),
            ),
            last_paid_at=Subquery(last_payment.values("paid_at")[:1]),
        )


class Account(TimeStampedModel):
    direction = models.CharField("Natureza", max_length=1, choices=Direction.choices)
    description = models.CharField("Descrição", max_length=200)
    category = models.ForeignKey(
        AccountType,
        on_delete=models.PROTECT,
        related_name="accounts",
        verbose_name="Categoria",
    )
    enrollment = models.OneToOneField(
        Enrollment,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="account",
        verbose_name="Matrícula",
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="accounts",
        verbose_name="Aluno",
    )
    guardian = models.ForeignKey(
        Guardian,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="accounts",
        verbose_name="Responsável financeiro",
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="accounts",
        verbose_name="Fornecedor",
    )
    issue_date = models.DateField("Data de emissão", default=timezone.localdate)
    gross_value = models.DecimalField("Valor bruto", **MONEY)
    discount_value = models.DecimalField("Desconto (R$)", default=ZERO, **MONEY)
    notes = models.TextField("Observações", blank=True)

    objects = AccountQuerySet.as_manager()

    def __str__(self):
        return f"{self.description}"

    @property
    def situation(self):
        """Needs with_installment_summary() annotations."""
        if self.installments_overdue:
            return "Vencida"
        if self.installments_pending:
            return "Em aberto"
        if self.installments_paid:
            return "Quitada"
        if self.installments_total:
            return "Cancelada"
        return "Sem parcelas"

    @property
    def net_value(self):
        return self.gross_value - self.discount_value

    @property
    def counterpart(self):
        return self.guardian or self.supplier

    class Meta:
        verbose_name = "Conta"
        verbose_name_plural = "Contas"
        ordering = ["-issue_date", "description"]
        constraints = [
            models.CheckConstraint(
                condition=Q(direction=Direction.RECEIVABLE, supplier__isnull=True)
                | Q(
                    direction=Direction.PAYABLE,
                    guardian__isnull=True,
                    enrollment__isnull=True,
                    student__isnull=True,
                ),
                name="account_counterpart_matches_direction",
            ),
            models.CheckConstraint(
                condition=Q(gross_value__gte=0), name="account_gross_value_not_negative"
            ),
            models.CheckConstraint(
                condition=Q(
                    discount_value__gte=0, discount_value__lte=models.F("gross_value")
                ),
                name="account_discount_within_gross_value",
            ),
        ]


class ReceivableManager(models.Manager.from_queryset(AccountQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(direction=Direction.RECEIVABLE)


class PayableManager(models.Manager.from_queryset(AccountQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(direction=Direction.PAYABLE)


class AccountReceivable(Account):
    objects = ReceivableManager()

    def save(self, *args, **kwargs):
        self.direction = Direction.RECEIVABLE
        super().save(*args, **kwargs)

    class Meta:
        proxy = True
        verbose_name = "Conta a receber"
        verbose_name_plural = "Contas a receber"


class AccountPayable(Account):
    objects = PayableManager()

    def save(self, *args, **kwargs):
        self.direction = Direction.PAYABLE
        super().save(*args, **kwargs)

    class Meta:
        proxy = True
        verbose_name = "Conta a pagar"
        verbose_name_plural = "Contas a pagar"


class InstallmentStatus(models.TextChoices):
    OPEN = "A", "Em aberto"
    PARTIAL = "P", "Pago parcialmente"
    PAID = "Q", "Quitado"
    CANCELLED = "C", "Cancelado"
    # Set when the bank writes off an unpaid slip (return code 09). The debt
    # is still owed, so it counts as pending.
    EXPIRED = "E", "Expirado"


PENDING_STATUSES = [
    InstallmentStatus.OPEN,
    InstallmentStatus.PARTIAL,
    InstallmentStatus.EXPIRED,
]


class InstallmentQuerySet(models.QuerySet):
    def with_balance(self):
        """Annotate `outstanding` (same rule as Installment.balance()) in SQL.

        A subquery is used instead of a join so the annotation can be summed.
        """
        money = DecimalField(**MONEY)
        paid_principal = (
            Payment.objects.filter(installment=OuterRef("pk"))
            .values("installment")
            .annotate(
                total=Sum(
                    F("amount")
                    - F("penalty")
                    - F("interest")
                    - F("monetary_adjust")
                    + F("discount")
                )
            )
            .values("total")
        )
        return self.annotate(
            outstanding=Case(
                When(status=InstallmentStatus.CANCELLED, then=Value(ZERO)),
                default=Greatest(
                    F("amount")
                    - Coalesce(
                        Subquery(paid_principal), Value(ZERO), output_field=money
                    ),
                    Value(ZERO),
                ),
                output_field=money,
            )
        )

    def pending(self):
        return self.filter(status__in=PENDING_STATUSES)

    def overdue(self):
        return self.pending().filter(due_date__lt=timezone.localdate())


class Installment(models.Model):
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="installments",
        verbose_name="Conta",
    )
    number = models.PositiveSmallIntegerField("Número da parcela")
    due_date = models.DateField("Vencimento")
    amount = models.DecimalField("Valor", **MONEY)
    status = models.CharField(
        "Situação",
        max_length=1,
        choices=InstallmentStatus.choices,
        default=InstallmentStatus.OPEN,
    )

    objects = InstallmentQuerySet.as_manager()

    def __str__(self):
        return f"{self.account} - {self.number}"

    def paid_principal(self):
        totals = self.payments.aggregate(
            amount=Sum("amount"),
            penalty=Sum("penalty"),
            interest=Sum("interest"),
            adjust=Sum("monetary_adjust"),
            discount=Sum("discount"),
        )
        totals = {key: value or ZERO for key, value in totals.items()}
        return (
            totals["amount"]
            - totals["penalty"]
            - totals["interest"]
            - totals["adjust"]
            + totals["discount"]
        )

    def balance(self):
        if self.status == InstallmentStatus.CANCELLED:
            return ZERO
        return max(self.amount - self.paid_principal(), ZERO)

    @property
    def is_overdue(self):
        return self.status in PENDING_STATUSES and self.due_date < timezone.localdate()

    def refresh_status(self):
        if self.status == InstallmentStatus.CANCELLED:
            return
        paid = self.paid_principal()
        if paid <= 0:
            status = InstallmentStatus.OPEN
        elif paid < self.amount:
            status = InstallmentStatus.PARTIAL
        else:
            status = InstallmentStatus.PAID
        if (
            self.status == InstallmentStatus.EXPIRED
            and status != InstallmentStatus.PAID
        ):
            return
        if status != self.status:
            self.status = status
            self.save(update_fields=["status"])

    class Meta:
        verbose_name = "Parcela"
        verbose_name_plural = "Parcelas"
        ordering = ["due_date", "account", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["account", "number"],
                name="unique_installment_number_per_account",
            ),
            models.CheckConstraint(
                condition=Q(amount__gte=0), name="installment_amount_not_negative"
            ),
        ]


class PaymentMethod(models.TextChoices):
    PIX = "PIX", "PIX"
    BOLETO = "BOL", "Boleto"
    CASH = "DIN", "Dinheiro"
    CREDIT_CARD = "CRE", "Cartão de crédito"
    DEBIT_CARD = "DEB", "Cartão de débito"
    TRANSFER = "TED", "Transferência"
    CHECK = "CHQ", "Cheque"


class Payment(TimeStampedModel):
    installment = models.ForeignKey(
        Installment,
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name="Parcela",
    )
    paid_at = models.DateField("Data do pagamento", default=timezone.localdate)
    amount = models.DecimalField(
        "Valor pago",
        help_text="Total recebido/pago, já incluindo multa, juros e correção",
        **MONEY,
    )
    penalty = models.DecimalField("Multa", default=ZERO, **MONEY)
    interest = models.DecimalField("Juros", default=ZERO, **MONEY)
    monetary_adjust = models.DecimalField("Correção", default=ZERO, **MONEY)
    discount = models.DecimalField(
        "Desconto",
        default=ZERO,
        help_text="Desconto concedido no pagamento (ex.: pontualidade); abate do saldo",
        **MONEY,
    )
    method = models.CharField(
        "Forma de pagamento", max_length=3, choices=PaymentMethod.choices
    )
    notes = models.CharField("Observações", max_length=200, blank=True)

    def __str__(self):
        return f"{self.installment} - {self.paid_at:%d/%m/%Y}"

    @property
    def principal(self):
        return (
            self.amount
            - self.penalty
            - self.interest
            - self.monetary_adjust
            + self.discount
        )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.installment.refresh_status()

    def delete(self, *args, **kwargs):
        installment = self.installment
        result = super().delete(*args, **kwargs)
        installment.refresh_status()
        return result

    class Meta:
        verbose_name = "Baixa"
        verbose_name_plural = "Baixas"
        ordering = ["-paid_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0), name="payment_amount_positive"
            ),
            models.CheckConstraint(
                condition=Q(penalty__gte=0, interest__gte=0, monetary_adjust__gte=0),
                name="payment_charges_not_negative",
            ),
            models.CheckConstraint(
                condition=Q(discount__gte=0), name="payment_discount_not_negative"
            ),
        ]
