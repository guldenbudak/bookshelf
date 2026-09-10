from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from .forms import RegisterForm
from .models import AccountApproval


class RegisterView(View):
    template_name = 'account/register.html'

    def get(self, request):
        form = RegisterForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Kaydın alındı. Hesabın yönetici onayından sonra aktifleşecek."
            )
            return redirect('login')

        return render(request, self.template_name, {'form': form})


class PendingView(LoginRequiredMixin, View):
    """Onayı beklemede olan ya da reddedilen kullanıcıya durumunu gösterir."""

    template_name = 'account/pending.html'

    def get(self, request):
        approval = AccountApproval.objects.filter(user=request.user).first()

        if approval and approval.status == AccountApproval.Status.APPROVED:
            return redirect('home')

        return render(request, self.template_name, {'approval': approval})
