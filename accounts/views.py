from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from django.db import transaction

from .decorators import approved_required, is_approved
from .forms import ProfileForm, ProfileSettingsForm, RegisterForm, SocialLinkFormSet
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


@login_required
def profile_detail(request, username=None):
    """Kullanıcı adı verilmezse kendi profilini, verilirse başkasınınkini gösterir."""

    if username is None:
        profile_user = request.user
    else:
        profile_user = get_object_or_404(User, username=username)

    is_own_profile = profile_user == request.user
    viewer_approved = is_approved(request.user)

    # Onay bekleyen kullanıcı yalnızca kendi profilini görebilir.kullanıcı kendisi değilse ve yönetici onayından geçmediyse
    if not is_own_profile and not viewer_approved:
        return redirect('pending')

    profile = profile_user.profile

    # Arkadaşlık kontrolü Aşama 3'te eklenecek; şimdilik herkes "arkadaş değil".
    is_friend = False
    can_see_books = is_own_profile or is_friend or profile.settings.books_public

    return render(request, 'account/profile.html', {
        'profile_user': profile_user,
        'profile': profile,
        'is_own_profile': is_own_profile,
        'can_see_books': can_see_books,
        'can_edit': is_own_profile and viewer_approved,
    })


@login_required
@approved_required
def profile_edit(request):
    """Profil, ayarlar ve sosyal bağlantılar tek sayfada birlikte kaydedilir."""

    profile = request.user.profile

    if request.method == 'POST':
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        settings_form = ProfileSettingsForm(request.POST, instance=profile.settings)
        link_formset = SocialLinkFormSet(request.POST, instance=profile)

        # all([...]) üçünü de doğrular; "and" olsaydı ilki hatalıyken
        # diğerlerinin hataları hesaplanmaz ve ekranda görünmezdi.
        if all([profile_form.is_valid(), settings_form.is_valid(), link_formset.is_valid()]):
            # Biri kaydedilip diğeri patlarsa profil yarım kalmasın.
            with transaction.atomic():
                profile_form.save()
                settings_form.save()
                link_formset.save()

            messages.success(request, "Profilin güncellendi.")
            return redirect('my-profile')
    else:
        profile_form = ProfileForm(instance=profile)
        settings_form = ProfileSettingsForm(instance=profile.settings)
        link_formset = SocialLinkFormSet(instance=profile)

    return render(request, 'account/profile_edit.html', {
        'profile_form': profile_form,
        'settings_form': settings_form,
        'link_formset': link_formset,
    })
