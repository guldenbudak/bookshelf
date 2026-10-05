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

    def test_gelen_istek_arkadaslar_sayfasinda_listelenir(self):
        FriendRequest.objects.create(from_user=self.bora, to_user=self.ayse)

        cevap = self.client.get(reverse('friends'))

        self.assertEqual([i.from_user for i in cevap.context['incoming']], [self.bora])
        self.assertIn('bora', cevap.content.decode())

    def test_kabul_edilen_istek_gelenler_listesinden_cikar(self):
        istek = FriendRequest.objects.create(from_user=self.bora, to_user=self.ayse)

        self.client.post(reverse('friend-request-accept', args=[istek.pk]))
        cevap = self.client.get(reverse('friends'))

        self.assertEqual(list(cevap.context['incoming']), [])


class TelefonDogrulamaTests(TestCase):
    """Telefon alanı serbest metin kabul etmemeli."""

    def setUp(self):
        self.kullanici = kullanici_olustur('telefoncu')
        self.client.force_login(self.kullanici)

    def profili_kaydet(self, phone):
        return self.client.post(reverse('profile-edit'), {
            'display_name': 'Ad', 'bio': '', 'birth_date': '', 'phone': phone,
            'theme': 'dark',
            # inline formset'in beklediği yönetim alanları
            'social_links-TOTAL_FORMS': '0', 'social_links-INITIAL_FORMS': '0',
            'social_links-MIN_NUM_FORMS': '0', 'social_links-MAX_NUM_FORMS': '5',
        })

    def test_gecersiz_numara_reddedilir(self):
        self.profili_kaydet('asdf')

        self.kullanici.profile.refresh_from_db()
        self.assertEqual(self.kullanici.profile.phone, '')

    def test_farkli_yazimlar_ayni_bicimde_saklanir(self):
        for yazim in ('0532 123 45 67', '+90 532 123 45 67', '(0532) 123-45-67'):
            with self.subTest(yazim=yazim):
                self.profili_kaydet(yazim)

                self.kullanici.profile.refresh_from_db()
                self.assertEqual(self.kullanici.profile.phone, '05321234567')
