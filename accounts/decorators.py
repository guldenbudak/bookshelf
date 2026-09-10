from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect

from accounts.models import AccountApproval


def approved_required(view_func):
    """Sadece yöneticinin onayladığı kullanıcıların view'a girmesine izin verir."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        approval = AccountApproval.objects.filter(user=request.user).first()
        if approval and approval.status == AccountApproval.Status.APPROVED:
            return view_func(request, *args, **kwargs)

        return redirect('pending')

    return wrapper
