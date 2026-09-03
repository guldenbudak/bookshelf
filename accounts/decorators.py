from accounts.models import AccountApproval
from django.shortcuts import redirect


def approved_required(view_func):
    def wrapper(request, *args, **kwargs):
        user = request.user
        approval = user.account_approval
        if approval.status == AccountApproval.Status.APPROVED:
            return view_func(request, *args, **kwargs)
        else:
            return redirect('pending')
    return wrapper
