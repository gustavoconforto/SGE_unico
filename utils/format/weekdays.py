from datetime import date, timedelta


def adjust_weekend(due_date: date) -> date:
    if due_date.weekday() == 5:
        return due_date + timedelta(days=2)

    if due_date.weekday() == 6:
        return due_date + timedelta(days=1)

    return due_date
