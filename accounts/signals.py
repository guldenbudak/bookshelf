from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile, AccountApproval


@receiver(post_save, sender=User)
def create_profile_and_approval(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        if instance.is_superuser:
            status = AccountApproval.Status.APPROVED
        else:
            status = AccountApproval.Status.PENDING

        AccountApproval.objects.create(user=instance, status=status)

