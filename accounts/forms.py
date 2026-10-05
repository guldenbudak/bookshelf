import re

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile
from django.forms import inlineformset_factory

from .models import Profile, ProfileSettings, SocialLink


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label="E-posta")

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Bu e-posta adresi zaten kullanılıyor.")
        return email


class ProfileForm(forms.ModelForm):
    MAX_AVATAR_SIZE = 2 * 1024 * 1024          # 2 MB
    ALLOWED_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp')

    class Meta:
        model = Profile
        fields = ('display_name', 'bio', 'avatar', 'birth_date', 'phone')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
            'birth_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')

        # Yeni dosya seçilmediyse elimizdeki kayıtlı dosyadır; onu tekrar
        # denetlemek gereksiz ve dosya diskten silinmişse hata verir.
        if not isinstance(avatar, UploadedFile):
            return avatar

        if not avatar.name.lower().endswith(self.ALLOWED_EXTENSIONS):
            izinli = ', '.join(self.ALLOWED_EXTENSIONS)
            raise forms.ValidationError(f"Yalnızca şu uzantılar yüklenebilir: {izinli}")

        if avatar.size > self.MAX_AVATAR_SIZE:
            mb = avatar.size / 1024 / 1024
            raise forms.ValidationError(
                f"Dosya 2 MB'ı geçemez. Seçtiğin dosya {mb:.1f} MB."
            )

        return avatar

    def clean_phone(self):
        """Telefonu denetler ve tek bir biçimde saklar.

        Kullanıcı numarayı boşluklu, tireli ya da +90'lı yazabilir. Hepsini
        aynı hâle getiriyoruz ki aynı numara veritabanında iki farklı
        görünümde durmasın.
        """
        phone = (self.cleaned_data.get('phone') or '').strip()

        # Alan zorunlu değil; boş bırakılabilir.
        if not phone:
            return ''

        # Ayırıcıları at, geriye yalnızca rakamlar (ve varsa +) kalsın.
        sade = re.sub(r'[\s()\-./]', '', phone)

        # Ülke kodunun üç yazılışını da 0'lı biçime çeviriyoruz.
        if sade.startswith('+90'):
            sade = '0' + sade[3:]
        elif sade.startswith('0090'):
            sade = '0' + sade[4:]
        elif len(sade) == 12 and sade.startswith('90'):
            sade = '0' + sade[2:]
        elif len(sade) == 10 and not sade.startswith('0'):
            sade = '0' + sade

        if not re.fullmatch(r'0\d{10}', sade):
            raise forms.ValidationError(
                "Telefon 11 haneli olmalı ve 0 ile başlamalı. Örnek: 0532 123 45 67"
            )

        return sade


class ProfileSettingsForm(forms.ModelForm):
    class Meta:
        model = ProfileSettings
        fields = ('books_public', 'show_email', 'theme', 'email_notifications')


SocialLinkFormSet = inlineformset_factory(
    Profile,
    SocialLink,
    fields=('platform', 'url'),
    extra=1,
    can_delete=True,
)
