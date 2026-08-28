from django.contrib.auth.models import User
from django.db import models

class AccountApproval(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending','Beklemede'
        APPROVED = 'approved','Onaylandı'
        REJECTED = 'rejected','Reddedildi'

    user = models.OneToOneField(User, on_delete=models.CASCADE,related_name='account_approval')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(User, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name='reviewed_accounts')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,related_name='profile')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username