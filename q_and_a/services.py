"""Extra points earned by attending Q&A sessions (plantões) in a bimester."""

from decimal import Decimal

from django.db.models import Count

from q_and_a.models import QandA

ZERO = Decimal(0)


def q_and_a_points(enrollment_ids, date_range, settings):
    """{enrollment pk: points} for the bimester in `date_range`.

    All or nothing: `settings.q_and_a_points` for at least
    `settings.q_and_a_min_sessions` sessions, zero below it.
    """
    attended = dict(
        QandA.objects.filter(
            enrollment_id__in=enrollment_ids, q_and_a_date__range=date_range
        )
        .order_by()
        .values("enrollment")
        .annotate(total=Count("pk"))
        .values_list("enrollment", "total")
    )
    return {
        pk: settings.q_and_a_points
        if attended.get(pk, 0) >= settings.q_and_a_min_sessions
        else ZERO
        for pk in enrollment_ids
    }
