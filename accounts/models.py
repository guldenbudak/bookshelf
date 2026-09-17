from datetime import date

from django.contrib.auth.models import User
from django.db import models
from django.db.models import F, Q
from django.urls import reverse

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

    def __str__(self):
        return f"{self.user.username} - {self.status}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,related_name='profile')
    display_name = models.CharField("Görünen ad", max_length=60, blank=True)
    bio = models.TextField("Hakkında", max_length=500, blank=True)
    avatar = models.ImageField("Profil fotoğrafı", upload_to='avatars/', blank=True)
    birth_date = models.DateField("Doğum tarihi", null=True, blank=True)
    phone = models.CharField("Telefon", max_length=20, blank=True)
    friends = models.ManyToManyField('self', symmetrical=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username

    def get_friends(self):
        """Arkadaş profillerini kullanıcılarıyla birlikte getirir."""
        return self.friends.select_related('user').order_by('user__username')

    def is_friend_with(self, other):
        return self.friends.filter(pk=other.pk).exists()

    def get_absolute_url(self):
        return reverse('profile-detail', kwargs={'username': self.user.username})

    @property
    def age(self):
        """Doğum tarihinden yaşı hesaplar. Veritabanında tutulmaz."""
        if not self.birth_date:
            return None

        bugun = date.today()
        yas = bugun.year - self.birth_date.year
        # Doğum günü bu yıl henüz gelmediyse bir yaş eksik.
        if (bugun.month, bugun.day) < (self.birth_date.month, self.birth_date.day):
            yas -= 1
        return yas

    @property
    def name(self):
        """Görünen ad girilmemişse kullanıcı adına düşer."""
        return self.display_name or self.user.username


class ProfileSettings(models.Model):
    class Theme(models.TextChoices):
        LIGHT = 'light', 'Açık'
        DARK = 'dark', 'Koyu'

    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='settings')
    books_public = models.BooleanField("Kitaplarım herkese açık", default=False)
    show_email = models.BooleanField("E-postamı göster", default=False)
    theme = models.CharField("Tema", max_length=10, choices=Theme.choices, default=Theme.LIGHT)
    email_notifications = models.BooleanField("E-posta bildirimleri", default=True)

    class Meta:
        verbose_name = "Profil ayarı"
        verbose_name_plural = "Profil ayarları"

    def __str__(self):
        return f"{self.profile.user.username} ayarları"


class SocialLink(models.Model):
    class Platform(models.TextChoices):
        INSTAGRAM = 'instagram', 'Instagram'
        X = 'x', 'X'
        LINKEDIN = 'linkedin', 'LinkedIn'
        GITHUB = 'github', 'GitHub'
        WEBSITE = 'website', 'Web sitesi'

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='social_links')
    platform = models.CharField("Platform", max_length=20, choices=Platform.choices)
    url = models.URLField("Adres")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['profile', 'platform'],
                name='uniq_profile_platform',
            )
        ]
        verbose_name = "Sosyal bağlantı"
        verbose_name_plural = "Sosyal bağlantılar"

    def __str__(self):
        return f"{self.profile.user.username} - {self.get_platform_display()}"


class FriendRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Beklemede'
        ACCEPTED = 'accepted', 'Kabul edildi'
        REJECTED = 'rejected', 'Reddedildi'

    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_requests')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_requests')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            # Bir yön için tek satır. Reddedilen istek tekrar gönderilmek
            # istendiğinde yeni satır açılmaz, bu satırın durumu güncellenir.
            models.UniqueConstraint(
                fields=['from_user', 'to_user'],
                name='uniq_friend_request',
            ),
            models.CheckConstraint(
                condition=~Q(from_user=F('to_user')),# kullanıcı kendisine istek atamasın
                name='no_self_request',
            ),
        ]
        verbose_name = "Arkadaşlık isteği"
        verbose_name_plural = "Arkadaşlık istekleri"

    def __str__(self):
        return f"{self.from_user.username} → {self.to_user.username} ({self.status})"


class Address(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='addresses')
    title = models.CharField("Başlık", max_length=30, help_text="Ev, İş...")
    city = models.CharField("İl", max_length=50)
    district = models.CharField("İlçe", max_length=50)
    full_address = models.TextField("Açık adres")
    is_default = models.BooleanField("Varsayılan adres", default=False)

    class Meta:
        ordering = ['-is_default', 'title']
        verbose_name = "Adres"
        verbose_name_plural = "Adresler"

    def __str__(self):
        return f"{self.profile.user.username} - {self.title}"