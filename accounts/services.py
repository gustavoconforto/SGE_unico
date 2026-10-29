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


def enrollment_due_dates(enrollment):
    """Monthly due dates on due_day, through December of the school year.

    Enrolling during the school year: the first installment is due on
    enrollment, then one per remaining month. Enrolling ahead: 12
    installments, January to December of the school year.
    """
    enrolled_at = enrollment.enrolled_at
    school_year = enrollment.enrollment_type.school_year.begins.year
    if enrolled_at.year == school_year:
        first, months = [enrolled_at], range(enrolled_at.month + 1, 13)
    else:
        first, months = [], range(1, 13)
    return first + [
        adjust_weekend(date(school_year, month, enrollment.due_day)) for month in months
    ]


@transaction.atomic
def create_enrollment_account(enrollment, category=None):
    enrollment.fill_contract_values()

    account = AccountReceivable.objects.create(
        description=f"Contrato {enrollment}"[:200],
        category=category or tuition_category(),
        enrollment=enrollment,
        student_id=enrollment.student_id,
        guardian=Guardian.objects.filter(
            student_links__student=enrollment.student_id,
            student_links__is_financial=True,
        ).first(),
        issue_date=enrollment.enrolled_at,
        gross_value=enrollment.gross_value,
        discount_value=enrollment.discount_value,
    )

    due_dates = enrollment_due_dates(enrollment)
    Installment.objects.bulk_create(
        Installment(
            account=account,
            number=number,
            due_date=due_date,
            amount=amount,
            status=InstallmentStatus.OPEN,
        )
        for number, (due_date, amount) in enumerate(
            zip(due_dates, enrollment_amounts(enrollment, len(due_dates))), start=1
        )
    )
    return account


def enrollment_amounts(enrollment, count):
    """The first installment is 1/12 of the contract with its own discounts;
    the other 11/12, with theirs, are split over the remaining installments.

    With a single installment (enrolling in December) it carries both parts.
    """
    if count == 1:
        return [enrollment.net_value]
    return [enrollment.first_net_value] + split_value(
        enrollment.remaining_net_value, count - 1
    )


def cancel_future_installments(enrollment):
    if not hasattr(enrollment, "account"):
        return 0
    return enrollment.account.installments.filter(
        status=InstallmentStatus.OPEN,
        due_date__gte=timezone.localdate(),
    ).update(status=InstallmentStatus.CANCELLED)
