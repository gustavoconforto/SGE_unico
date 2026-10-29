from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.services import cancel_future_installments, create_enrollment_account

from .models import ENDED_EARLY, Enrollment


@receiver(post_save, sender=Enrollment)
def create_neededDocuments(sender, instance, created, **kwargs):
    if created:
        create_enrollment_account(instance)
        instance.sync_documents()

    elif instance.status in ENDED_EARLY:
        cancel_future_installments(instance)
