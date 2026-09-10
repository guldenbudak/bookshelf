from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from .forms import RegisterForm


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
