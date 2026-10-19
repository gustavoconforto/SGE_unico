from decimal import ROUND_HALF_UP, Decimal
from hashlib import sha256

from django.db import transaction
from django.utils import timezone

from accounts.models import (
    PENDING_STATUSES,
    ZERO,
    Direction,
    Installment,
    InstallmentStatus,
    Payment,
    PaymentMethod,
)
from billing import cnab400
from billing.models import (
    LIVE_SLIP_STATUSES,
    NOSSO_NUMERO_PREFIX,
    BankSettings,
    BankSlip,
    EventStatus,
    Occurrence,
    Remittance,
    ReturnEvent,
    ReturnFile,
    SlipStatus,
)


class BillingError(Exception):
    """Business error shown to the user as is."""


# REMITTANCE


def remittance_candidates():
    """Receivable installments with a balance and no slip that may still be paid."""
    return (
        Installment.objects.filter(
            account__direction=Direction.RECEIVABLE, status__in=PENDING_STATUSES
        )
        .exclude(bank_slips__status__in=LIVE_SLIP_STATUSES)
        .select_related(
            "account__guardian", "account__enrollment__enrollment_type"
        )
        .with_balance()
        .filter(outstanding__gt=0)
    )


def payer_problems(installment, today=None):
    """Reasons that prevent sending the installment to the bank (empty if none)."""
    today = today or timezone.localdate()
    guardian = installment.account.guardian
    if guardian is None:
        return ["Conta sem responsável financeiro"]
    problems = []
    if len(guardian.cpf or "") != 11 or not guardian.cpf.isdigit():
        problems.append("CPF do responsável inválido")
    if not guardian.address:
        problems.append("Responsável sem endereço")
    if len(guardian.zip_code or "") != 8 or not guardian.zip_code.isdigit():
        problems.append("CEP do responsável inválido")
    if installment.due_date < today:
        problems.append("Vencimento já passou; altere a data antes de enviar")
    return problems


def punctuality_discount(installment, amount):
    enrollment = installment.account.enrollment
    if enrollment is None:
        return ZERO
    discount = enrollment.enrollment_type.punctuality_discount
    # The bank requires the discount to be below the slip amount.
    return discount if ZERO < discount < amount else ZERO


def daily_interest(amount, monthly_percent):
    return (amount * monthly_percent / Decimal(100) / 30).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _payer(guardian):
    address = " ".join(part for part in (guardian.address, guardian.neighborhood) if part)
    return cnab400.Payer(
        tax_id=guardian.cpf,
        name=guardian.name,
        address=address,
        zip_code=guardian.zip_code,
    )


def write_off_candidates():
    """Registered slips whose installment was cancelled or paid another way.

    The bank still charges the original amount, so these must be written off
    (movement code 02) before the installment can get a new slip.
    """
    slips = list(
        BankSlip.objects.filter(status=SlipStatus.REGISTERED)
        .select_related("remittance", "installment__account__guardian")
        .order_by("due_date", "pk")
    )
    balances = dict(
        Installment.objects.with_balance()
        .filter(pk__in=[slip.installment_id for slip in slips])
        .values_list("pk", "outstanding")
    )
    return [
        slip
        for slip in slips
        if slip.installment.status == InstallmentStatus.CANCELLED
        or balances[slip.installment_id] < slip.amount
    ]


def _title(slip, settings, issue_date, movement_code="01"):
    guardian = slip.installment.account.guardian
    if guardian is None:
        raise BillingError(f"Boleto {slip}: conta sem responsável financeiro.")
    return cnab400.Title(
        participant_control=str(slip.pk),
        document_number=str(slip.installment_id),
        nosso_numero=slip.nosso_numero,
        due_date=slip.due_date,
        amount=slip.amount,
        issue_date=issue_date,
        payer=_payer(guardian),
        movement_code=movement_code,
        fine_percent=settings.fine_percent,
        daily_interest=daily_interest(slip.amount, settings.monthly_interest_percent),
        discount_deadline=slip.due_date if slip.discount else None,
        discount_amount=slip.discount,
    )


@transaction.atomic
def create_remittance(installment_ids=(), write_off_slip_ids=(), generation_date=None):
    """One file with new slips (movement 01) and write-off requests (02)."""
    generation_date = generation_date or timezone.localdate()
    settings = BankSettings.objects.select_for_update().filter(pk=1).first()
    if settings is None:
        raise BillingError("Cadastre a configuração bancária antes de gerar remessas.")

    installments = [
        installment
        for installment in remittance_candidates()
        .filter(pk__in=installment_ids)
        .order_by("due_date", "pk")
        if not payer_problems(installment, generation_date)
    ]
    write_offs = [
        slip for slip in write_off_candidates() if slip.pk in set(write_off_slip_ids)
    ]
    if not installments and not write_offs:
        raise BillingError(
            "Nenhuma parcela ou pedido de baixa selecionado está apto para a remessa."
        )

    settings.last_remittance_number += 1
    settings.save(update_fields=["last_remittance_number", "updated_at"])
    remittance = Remittance.objects.create(
        number=settings.last_remittance_number, generated_at=generation_date
    )

    titles = []
    for slip in write_offs:
        titles.append(
            _title(slip, settings, slip.remittance.generated_at, movement_code="02")
        )
        slip.status = SlipStatus.WRITE_OFF_REQUESTED
        slip.write_off_remittance = remittance
        slip.save(update_fields=["status", "write_off_remittance", "updated_at"])

    for installment in installments:
        amount = installment.outstanding
        slip = BankSlip.objects.create(
            remittance=remittance,
            installment=installment,
            nosso_numero=f"tmp{installment.pk}",
            due_date=installment.due_date,
            amount=amount,
            discount=punctuality_discount(installment, amount),
        )
        slip.assign_nosso_numero(settings.carteira)
        slip.save(update_fields=["nosso_numero", "nosso_numero_dv"])
        titles.append(_title(slip, settings, generation_date))

    config = cnab400.RemittanceConfig(
        beneficiary=settings.beneficiary,
        remittance_number=remittance.number,
        generation_date=generation_date,
    )
    try:
        payload = cnab400.generate_remittance(config, titles)
    except ValueError as exc:
        raise BillingError(f"Erro ao gerar o arquivo: {exc}") from exc
    remittance.content = payload.decode("ascii")
    remittance.save(update_fields=["content"])
    return remittance


@transaction.atomic
def delete_remittance(remittance):
    """Delete a remittance the bank hasn't processed yet."""
    if remittance.slips.exclude(status=SlipStatus.GENERATED).exists() or (
        remittance.write_off_slips.exclude(
            status=SlipStatus.WRITE_OFF_REQUESTED
        ).exists()
    ):
        raise BillingError(
            "Esta remessa já foi processada pelo banco e não pode ser deletada."
        )
    remittance.write_off_slips.update(
        status=SlipStatus.REGISTERED, write_off_remittance=None
    )
    remittance.slips.all().delete()
    remittance.delete()
    # Free the number when it was the last one, so the next file reuses it.
    BankSettings.objects.filter(
        pk=1, last_remittance_number=remittance.number
    ).update(last_remittance_number=remittance.number - 1)


# RETURN


def _is_ours(parsed):
    # Slips from the previous system use another prefix; blank numbers fall
    # back to the participant control, which holds our slip id.
    return not parsed.nosso_numero or parsed.nosso_numero.startswith(NOSSO_NUMERO_PREFIX)


def _find_slip(parsed):
    if parsed.nosso_numero:
        return BankSlip.objects.filter(nosso_numero=parsed.nosso_numero[:11]).first()
    if parsed.participant_control.isdigit():
        return BankSlip.objects.filter(pk=int(parsed.participant_control)).first()
    return None


def _settle(event, parsed, slip, return_file):
    if slip.events.filter(payment__isnull=False).exists():
        raise BillingError("Boleto já liquidado em outro retorno")
    if parsed.amount_paid <= 0:
        raise BillingError("Liquidação sem valor pago")
    paid_at = parsed.occurrence_date or parsed.credit_date
    if paid_at is None:
        raise BillingError("Liquidação sem data")
    installment = Installment.objects.select_for_update().get(pk=slip.installment_id)
    if installment.status == InstallmentStatus.CANCELLED:
        raise BillingError("Parcela cancelada; registre a devolução manualmente")
    principal = parsed.amount_paid - parsed.interest_amount + parsed.discount_amount
    balance = installment.balance()
    if principal <= 0 or principal > balance:
        raise BillingError(
            f"Valor principal (R$ {principal}) incompatível com o saldo da parcela "
            f"(R$ {balance}); registre a baixa manualmente"
        )
    event.payment = Payment.objects.create(
        installment=installment,
        paid_at=paid_at,
        amount=parsed.amount_paid,
        interest=parsed.interest_amount,
        discount=parsed.discount_amount,
        method=PaymentMethod.BOLETO,
        notes=f"Boleto {slip} - retorno {return_file.name}"[:200],
    )
    slip.status = SlipStatus.PAID


def _reverse(event, slip):
    settled = (
        slip.events.filter(payment__isnull=False)
        .select_related("payment")
        .order_by("-pk")
        .first()
    )
    if settled is None:
        raise BillingError("Nenhuma baixa deste boleto para estornar")
    settled.payment.delete()  # refreshes the installment status
    slip.status = SlipStatus.REVERSED
    event.message = "Baixa do boleto excluída"


def _apply(event, parsed, slip, return_file):
    code = parsed.occurrence_code
    if code == Occurrence.ENTRY_CONFIRMED:
        if slip.status == SlipStatus.GENERATED:
            slip.status = SlipStatus.REGISTERED
    elif code == Occurrence.ENTRY_REJECTED:
        slip.status = SlipStatus.REJECTED
        event.message = "Boleto rejeitado; a parcela pode ser enviada em nova remessa"
    elif parsed.is_settlement:
        _settle(event, parsed, slip, return_file)
    elif parsed.is_reversal:
        _reverse(event, slip)
    elif code == Occurrence.EXPIRED:
        slip.status = SlipStatus.EXPIRED
        Installment.objects.filter(
            pk=slip.installment_id,
            status__in=[InstallmentStatus.OPEN, InstallmentStatus.PARTIAL],
        ).update(status=InstallmentStatus.EXPIRED)
    elif code == Occurrence.WRITTEN_OFF:
        # Confirms a write-off request (movement 02), sent after the
        # installment was cancelled or paid another way.
        slip.status = SlipStatus.WRITTEN_OFF
        balance = slip.installment.balance()
        if balance > 0:
            event.message = (
                f"Parcela ainda possui saldo de R$ {balance}; "
                "pode ser enviada em nova remessa"
            )
    elif code == Occurrence.WRITE_OFF_REJECTED:
        if slip.status == SlipStatus.WRITE_OFF_REQUESTED:
            slip.status = SlipStatus.REGISTERED
        event.message = "Pedido de baixa rejeitado; o boleto continua registrado"
    else:
        event.status = EventStatus.IGNORED
        event.message = "Ocorrência sem ação no sistema"
        return
    slip.save(update_fields=["status", "updated_at"])


@transaction.atomic
def import_return(name, payload):
    try:
        data = cnab400.parse_return(payload)
    except ValueError as exc:
        raise BillingError(f"Arquivo inválido: {exc}") from exc

    settings = BankSettings.load()
    if settings is None:
        raise BillingError("Cadastre a configuração bancária antes de importar retornos.")
    if data.company_code.lstrip("0") != settings.company_code.lstrip("0"):
        raise BillingError("O arquivo pertence a outro código de empresa.")

    digest = sha256(payload).hexdigest()
    if ReturnFile.objects.filter(sha256=digest).exists():
        raise BillingError("Este arquivo de retorno já foi importado.")
    return_file = ReturnFile.objects.create(
        name=name[:255],
        sha256=digest,
        file_date=data.file_date,
        content=payload.decode("ascii"),
    )

    known = set(
        ReturnEvent.objects.filter(
            fingerprint__in=[parsed.fingerprint for parsed in data.events]
        ).values_list("fingerprint", flat=True)
    )
    for parsed in data.events:
        if parsed.fingerprint in known:
            continue
        event = ReturnEvent(
            return_file=return_file,
            sequence=parsed.sequence,
            fingerprint=parsed.fingerprint,
            nosso_numero=parsed.nosso_numero,
            occurrence_code=parsed.occurrence_code,
            occurrence_date=parsed.occurrence_date,
            due_date=parsed.due_date,
            title_amount=parsed.title_amount,
            amount_paid=parsed.amount_paid,
            interest=parsed.interest_amount,
            discount=parsed.discount_amount,
            credit_date=parsed.credit_date,
            reason_codes=" ".join(parsed.reason_codes),
            status=EventStatus.PROCESSED,
        )
        slip = _find_slip(parsed) if _is_ours(parsed) else None
        if not _is_ours(parsed):
            event.status = EventStatus.IGNORED
            event.message = "Boleto não emitido por este sistema"
        elif slip is None:
            event.status = EventStatus.ERROR
            event.message = "Boleto não localizado"
        else:
            event.bank_slip = slip
            try:
                with transaction.atomic():
                    _apply(event, parsed, slip, return_file)
            except BillingError as exc:
                event.payment = None
                event.status = EventStatus.ERROR
                event.message = str(exc)
        event.save()
    return return_file
