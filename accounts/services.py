import calendar
from datetime import date
from decimal import ROUND_DOWN, Decimal

from django.db import transaction
from django.utils import timezone

from accounts.models import (
    AccountReceivable,
    AccountType,
    Direction,
    Installment,
    InstallmentStatus,
)
from students.models import Guardian
from utils.format.weekdays import adjust_weekend

TUITION_CATEGORY = "Mensalidade"


def add_months(start, months, day):
    month_index = start.month - 1 + months
    year, month = start.year + month_index // 12, month_index % 12 + 1
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def build_installments(account, count, first_due_date):
    return [
        Installment(
            account=account,
            number=number,
            due_date=add_months(first_due_date, number - 1, first_due_date.day),
            amount=amount,
        )
        for number, amount in enumerate(split_value(account.net_value, count), start=1)
    ]


def split_value(total, count):
    part = (total / count).quantize(Decimal("0.01"), ROUND_DOWN)
    return [total - part * (count - 1)] + [part] * (count - 1)


def tuition_category():
    return AccountType.objects.get_or_create(
        name=TUITION_CATEGORY, defaults={"direction": Direction.RECEIVABLE}
    )[0]


@transaction.atomic
def create_enrollment_account(enrollment, category=None):
    enrollment.fill_contract_values()

    account = AccountReceivable.objects.create(
        description=f"Contrato {enrollment}"[:200],
        category=category or tuition_category(),
        enrollment=enrollment,
        guardian=Guardian.objects.filter(
            student_links__student=enrollment.student_id,
            student_links__is_financial=True,
        ).first(),
        issue_date=enrollment.enrolled_at,
        gross_value=enrollment.gross_value,
        discount_value=enrollment.discount_value,
    )

    if str(enrollment.enrolled_at.year) == str(enrollment.enrollment_type.school_year):
        month_number = int(enrollment.enrolled_at.month)
        installment_number = 12 - month_number + 1
        installment_value = account.net_value / installment_number

        Installment.objects.create(
            account=account,
            number=1,
            due_date=enrollment.enrolled_at,
            amount=installment_value,
            status=InstallmentStatus.OPEN,
        )

        for i in range(installment_number - 1):
            due_date = adjust_weekend(
                date(
                    int(enrollment.enrolled_at.year),
                    int(enrollment.enrolled_at.month) + i + 1,
                    enrollment.due_day,
                )
            )
            Installment.objects.create(
                account=account,
                number=i + 2,
                due_date=due_date,
                amount=installment_value,
                status=InstallmentStatus.OPEN,
            )

    else:
        installment_number = 12
        month_number = int(enrollment.enrolled_at.month)
        installment_value = account.net_value / installment_number

        Installment.objects.create(
            account=account,
            number=1,
            due_date=enrollment.enrolled_at,
            amount=installment_value,
            status=InstallmentStatus.OPEN,
        )

        for i in range(installment_number - 1):
            due_date = adjust_weekend(
                date(int(enrollment.enrolled_at.year), 2 + i, enrollment.due_day)
            )
            Installment.objects.create(
                account=account,
                number=i + 2,
                due_date=due_date,
                amount=installment_value,
                status=InstallmentStatus.OPEN,
            )
    return account


def cancel_future_installments(enrollment):
    """When a contract ends early, installments not yet due are cancelled; overdue ones are still owed."""
    if not hasattr(enrollment, "account"):
        return 0
    return enrollment.account.installments.filter(
        status=InstallmentStatus.OPEN,
        due_date__gte=timezone.localdate(),
    ).update(status=InstallmentStatus.CANCELLED)
