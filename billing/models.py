from decimal import Decimal

from django.db import models
from django.db.models import Q
from django.utils import timezone

from accounts.models import MONEY, ZERO, Installment, Payment
from base.models import TimeStampedModel
from billing.cnab400 import Beneficiary, nosso_numero_dv, remittance_filename

# "Nosso número" = this prefix + the slip id, zero-filled to 11 digits.
NOSSO_NUMERO_PREFIX = "2000"
NOSSO_NUMERO_LENGTH = 11


class BankSettings(TimeStampedModel):
    """Bradesco beneficiary data. A single row (pk=1), edited on one screen."""

    company_code = models.CharField(
        "Código da empresa",
        max_length=20,
        help_text="Código do beneficiário informado pelo Bradesco (somente números)",
    )
    company_name = models.CharField("Razão social", max_length=100)
    carteira = models.CharField("Carteira", max_length=3, default="09")
    agency = models.CharField("Agência", max_length=5, help_text="Sem dígito")
    account = models.CharField("Conta corrente", max_length=7, help_text="Sem dígito")
    account_digit = models.CharField("Dígito da conta", max_length=1)
    fine_percent = models.DecimalField(
        "Multa (%)", max_digits=4, decimal_places=2, default=Decimal("2.00")
    )
    monthly_interest_percent = models.DecimalField(
        "Juros ao mês (%)", max_digits=4, decimal_places=2, default=Decimal("1.00")
    )
    last_remittance_number = models.PositiveIntegerField(
        "Última remessa",
        default=0,
        help_text="Número da última remessa enviada ao banco; a próxima usa o seguinte",
    )

    def __str__(self):
        return f"{self.company_name}"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        return cls.objects.filter(pk=1).first()

    @property
    def beneficiary(self):
        return Beneficiary(
            company_code=self.company_code,
            name=self.company_name,
            carteira=self.carteira,
            agency=self.agency,
            account=self.account,
            account_digit=self.account_digit,
        )

    class Meta:
        verbose_name = "Configuração bancária"
        verbose_name_plural = "Configurações bancárias"
        ordering = ["pk"]
        constraints = [
            models.CheckConstraint(
                condition=Q(fine_percent__gte=0, monthly_interest_percent__gte=0),
                name="bank_settings_rates_not_negative",
            ),
        ]


class Remittance(TimeStampedModel):
    number = models.PositiveIntegerField("Número", unique=True)
    generated_at = models.DateField("Data de geração", default=timezone.localdate)
    content = models.TextField("Conteúdo do arquivo")

    def __str__(self):
        return f"Remessa {self.number}"

    @property
    def filename(self):
        return remittance_filename(self.number)

    class Meta:
        verbose_name = "Remessa"
        verbose_name_plural = "Remessas"
        ordering = ["-number"]


class SlipStatus(models.TextChoices):
    GENERATED = "G", "Gerado"
    REGISTERED = "R", "Registrado"
    WRITE_OFF_REQUESTED = "S", "Baixa solicitada"
    REJECTED = "J", "Rejeitado"
    PAID = "L", "Liquidado"
    EXPIRED = "E", "Baixado por decurso de prazo"
    WRITTEN_OFF = "B", "Baixado pela agência"
    REVERSED = "X", "Pagamento estornado"


# A live slip may still be paid at the bank, so its installment can't be
# sent again. A requested write-off stays live until the bank confirms it.
LIVE_SLIP_STATUSES = [
    SlipStatus.GENERATED,
    SlipStatus.REGISTERED,
    SlipStatus.WRITE_OFF_REQUESTED,
]


class BankSlip(TimeStampedModel):
    remittance = models.ForeignKey(
        Remittance,
        on_delete=models.PROTECT,
        related_name="slips",
        verbose_name="Remessa",
    )
    write_off_remittance = models.ForeignKey(
        Remittance,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="write_off_slips",
        verbose_name="Remessa do pedido de baixa",
    )
    installment = models.ForeignKey(
        Installment,
        on_delete=models.PROTECT,
        related_name="bank_slips",
        verbose_name="Parcela",
    )
    nosso_numero = models.CharField("Nosso número", max_length=11, unique=True)
    nosso_numero_dv = models.CharField("Dígito do nosso número", max_length=1)
    due_date = models.DateField("Vencimento")
    amount = models.DecimalField("Valor", **MONEY)
    discount = models.DecimalField("Desconto de pontualidade", default=ZERO, **MONEY)
    status = models.CharField(
        "Situação",
        max_length=1,
        choices=SlipStatus.choices,
        default=SlipStatus.GENERATED,
    )

    def __str__(self):
        return f"{self.nosso_numero}-{self.nosso_numero_dv}"

    def assign_nosso_numero(self, carteira):
        number = f"{NOSSO_NUMERO_PREFIX}{self.pk:0{NOSSO_NUMERO_LENGTH - len(NOSSO_NUMERO_PREFIX)}d}"
        if len(number) > NOSSO_NUMERO_LENGTH:
            raise ValueError("Faixa de nosso número esgotada.")
        self.nosso_numero = number
        self.nosso_numero_dv = nosso_numero_dv(carteira, number)

    class Meta:
        verbose_name = "Boleto"
        verbose_name_plural = "Boletos"
        ordering = ["-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["installment"],
                condition=Q(status__in=LIVE_SLIP_STATUSES),
                name="unique_live_slip_per_installment",
            ),
            models.CheckConstraint(
                condition=Q(amount__gt=0), name="bank_slip_amount_positive"
            ),
            models.CheckConstraint(
                condition=Q(discount__gte=0, discount__lt=models.F("amount")),
                name="bank_slip_discount_below_amount",
            ),
        ]


class ReturnFile(TimeStampedModel):
    name = models.CharField("Nome do arquivo", max_length=255)
    sha256 = models.CharField("Hash SHA-256", max_length=64, unique=True)
    file_date = models.DateField("Data do arquivo", null=True, blank=True)
    content = models.TextField("Conteúdo do arquivo")

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Arquivo de retorno"
        verbose_name_plural = "Arquivos de retorno"
        ordering = ["-created_at"]


class Occurrence(models.TextChoices):
    ENTRY_CONFIRMED = "02", "Entrada confirmada"
    ENTRY_REJECTED = "03", "Entrada rejeitada"
    PAID = "06", "Liquidação normal"
    EXPIRED = "09", "Baixado por decurso de prazo"
    WRITTEN_OFF = "10", "Baixado conforme instruções da agência"
    REBATE_GRANTED = "12", "Abatimento concedido"
    REBATE_CANCELLED = "13", "Abatimento cancelado"
    DUE_DATE_CHANGED = "14", "Vencimento alterado"
    PAID_AT_NOTARY = "15", "Liquidação em cartório"
    PAID_BY_CHECK = "16", "Título pago em cheque vinculado"
    PAID_AFTER_WRITEOFF = "17", "Liquidação após baixa"
    PAYMENT_CANCELLED = "22", "Pagamento cancelado"
    WRITE_OFF_REJECTED = "27", "Baixa rejeitada"
    PAYMENT_REVERSED = "40", "Estorno de pagamento"


class EventStatus(models.TextChoices):
    PROCESSED = "P", "Processado"
    ERROR = "E", "Erro"
    IGNORED = "I", "Ignorado"


class ReturnEvent(models.Model):
    return_file = models.ForeignKey(
        ReturnFile,
        on_delete=models.PROTECT,
        related_name="events",
        verbose_name="Arquivo de retorno",
    )
    sequence = models.PositiveIntegerField("Sequência")
    fingerprint = models.CharField("Hash da linha", max_length=64, unique=True)
    bank_slip = models.ForeignKey(
        BankSlip,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="events",
        verbose_name="Boleto",
    )
    # SET_NULL: deleting the payment by hand (or by a reversal) must not be
    # blocked by the event that created it.
    payment = models.OneToOneField(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="return_event",
        verbose_name="Baixa",
    )
    nosso_numero = models.CharField("Nosso número", max_length=20)
    occurrence_code = models.CharField(
        "Ocorrência", max_length=2, choices=Occurrence.choices
    )
    occurrence_date = models.DateField("Data da ocorrência", null=True, blank=True)
    due_date = models.DateField("Vencimento", null=True, blank=True)
    title_amount = models.DecimalField("Valor do título", default=ZERO, **MONEY)
    amount_paid = models.DecimalField("Valor pago", default=ZERO, **MONEY)
    interest = models.DecimalField("Juros/multa", default=ZERO, **MONEY)
    discount = models.DecimalField("Desconto", default=ZERO, **MONEY)
    credit_date = models.DateField("Data do crédito", null=True, blank=True)
    reason_codes = models.CharField("Motivos", max_length=20, blank=True)
    status = models.CharField(
        "Resultado", max_length=1, choices=EventStatus.choices
    )
    message = models.CharField("Mensagem", max_length=300, blank=True)

    def __str__(self):
        return f"{self.return_file} - {self.sequence}"

    class Meta:
        verbose_name = "Ocorrência de retorno"
        verbose_name_plural = "Ocorrências de retorno"
        ordering = ["return_file", "sequence"]
