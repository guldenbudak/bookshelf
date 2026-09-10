from django.contrib import admin
from django.utils import timezone
from accounts.models import AccountApproval, Profile
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin


@admin.action(description="Seçili kullanıcıları onayla")
def approve_users(modeladmin, request, queryset):
    queryset.update(
        status=AccountApproval.Status.APPROVED,
        reviewed_by=request.user,
        reviewed_at=timezone.now()
    )


@admin.action(description="Seçili kullanıcıları reddet")
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


class ProfileInline(admin.StackedInline):
    model = Profile


class AccountApprovalInline(admin.StackedInline):
    model = AccountApproval
    fk_name = 'user'


admin.site.register(AccountApproval, AccountApprovalAdmin)


class CustomUserAdmin(UserAdmin):
    inlines = [ProfileInline, AccountApprovalInline]


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
