from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import AccountApproval, FriendRequest

PAROLA = 'Test12345!'


def kullanici_olustur(username, onayli=True):
    """Test kullanıcısı üretir. Profil, ayar ve onay kaydı signal ile gelir."""
    user = User.objects.create_user(username=username, password=PAROLA)
    if onayli:
        user.account_approval.status = AccountApproval.Status.APPROVED
        user.account_approval.save()
    return user


class OnayAkisiTests(TestCase):
    """Hesap onayı olmadan uygulamanın kullanılamadığını doğrular."""

    def test_onaysiz_kullanici_korumali_sayfaya_erisemez(self):
        self.client.force_login(kullanici_olustur('bekleyen', onayli=False))

        cevap = self.client.get(reverse('book-list'))

        self.assertRedirects(cevap, reverse('pending'))

    def test_onayli_kullanici_erisebilir(self):
        self.client.force_login(kullanici_olustur('onayli'))

        cevap = self.client.get(reverse('book-list'))

        self.assertEqual(cevap.status_code, 200)

    def test_reddedilen_kullanici_da_erisemez(self):
        reddedilen = kullanici_olustur('reddedilen', onayli=False)
        reddedilen.account_approval.status = AccountApproval.Status.REJECTED
        reddedilen.account_approval.save()
        self.client.force_login(reddedilen)

        cevap = self.client.get(reverse('book-list'))

        self.assertRedirects(cevap, reverse('pending'))


class ArkadaslikIstegiTests(TestCase):
    def setUp(self):
        self.ayse = kullanici_olustur('ayse')
        self.bora = kullanici_olustur('bora')
        self.client.force_login(self.ayse)

    def test_kullanici_kendine_istek_gonderemez(self):
        cevap = self.client.post(
            reverse('friend-request-send', args=['ayse']), follow=True
        )

        self.assertEqual(FriendRequest.objects.count(), 0)
        mesajlar = [str(m) for m in cevap.context['messages']]
        self.assertIn("Kendine arkadaşlık isteği gönderemezsin.", mesajlar)

    def test_istegi_yalnizca_alicisi_kabul_edebilir(self):
        istek = FriendRequest.objects.create(from_user=self.ayse, to_user=self.bora)

        # Gönderen kendi isteğini kabul etmeye çalışıyor.
        cevap = self.client.post(reverse('friend-request-accept', args=[istek.pk]))

        self.assertEqual(cevap.status_code, 404)
        istek.refresh_from_db()
        self.assertEqual(istek.status, FriendRequest.Status.PENDING)
        self.assertFalse(self.ayse.profile.is_friend_with(self.bora.profile))

    def test_karsilikli_istek_dogrudan_arkadaslik_kurar(self):
        FriendRequest.objects.create(from_user=self.bora, to_user=self.ayse)

        self.client.post(reverse('friend-request-send', args=['bora']))

        self.assertTrue(self.ayse.profile.is_friend_with(self.bora.profile))
