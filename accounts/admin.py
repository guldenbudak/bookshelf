from django.contrib import admin
from django.utils import timezone
from accounts.models import AccountApproval


def approve_users(modeladmin, request, queryset):
    queryset.update(
        status=AccountApproval.Status.APPROVED,
        reviewed_by=request.user,
        reviewed_at=timezone.now()
    )


def reject_users(modeladmin, request, queryset):
    queryset.update(
        status=AccountApproval.Status.REJECTED,
        reviewed_by=request.user,
        reviewed_at=timezone.now()
    )


class AccountApprovalAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "reason", "created_at", "reviewed_by", "reviewed_at")
    list_filter = ("status",)
    search_fields = ("user__username", "user__email")
    actions = [approve_users, reject_users]


admin.site.register(AccountApproval, AccountApprovalAdmin)
