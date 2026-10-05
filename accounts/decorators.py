from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect

from accounts.models import AccountApproval


def is_approved(user):
    """Kullanıcının yönetici onayından geçip geçmediğini söyler."""
    approval = AccountApproval.objects.filter(user=user).first()
    return bool(approval and approval.status == AccountApproval.Status.APPROVED)


def approved_required(view_func):
    """Sadece yöneticinin onayladığı kullanıcıların view'a girmesine izin verir."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        if is_approved(request.user):
            return view_func(request, *args, **kwargs)

        return redirect('pending')

    return wrapper
