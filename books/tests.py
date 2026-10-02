from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounts.tests import kullanici_olustur
from books.models import Book, Category, Comment, Favorite


def kitap_olustur(owner, title='Deneme Kitabı'):
    kategori, _ = Category.objects.get_or_create(name='Test Kategorisi')
    return Book.objects.create(
        title=title, author='Yazar', category=kategori,
        page_count=100, owner=owner,
    )


class KitapGorunurluguTests(TestCase):
    """Arkadaşlık, bir kitabın görülüp görülemeyeceğini belirler."""

    def setUp(self):
        self.sahip = kullanici_olustur('sahip')
        self.yabanci = kullanici_olustur('yabanci')
        self.kitap = kitap_olustur(self.sahip)

    def test_arkadas_olmayan_baskasinin_kitabini_goremez(self):
        self.client.force_login(self.yabanci)

        cevap = self.client.get(reverse('book-detail', args=[self.kitap.pk]))

        # 403 değil 404: kitabın var olduğu bilgisi bile sızmamalı.
        self.assertEqual(cevap.status_code, 404)

    def test_arkadas_olan_gorebilir(self):
        self.yabanci.profile.friends.add(self.sahip.profile)
        self.client.force_login(self.yabanci)

        cevap = self.client.get(reverse('book-detail', args=[self.kitap.pk]))

        self.assertEqual(cevap.status_code, 200)

    def test_kitapligini_herkese_acan_kullanicinin_kitabi_gorunur(self):
        self.sahip.profile.settings.books_public = True
        self.sahip.profile.settings.save()
        self.client.force_login(self.yabanci)

        cevap = self.client.get(reverse('book-detail', args=[self.kitap.pk]))

        self.assertEqual(cevap.status_code, 200)


class KitapSahipligiTests(TestCase):
    def setUp(self):
        self.sahip = kullanici_olustur('sahip')
        self.baskasi = kullanici_olustur('baskasi')
        # Kitabı görebilsin ama sahibi olmasın: silme yetkisini ölçüyoruz.
        self.baskasi.profile.friends.add(self.sahip.profile)
        self.kitap = kitap_olustur(self.sahip)

    def test_sahibi_olmayan_kullanici_kitabi_silemez(self):
        self.client.force_login(self.baskasi)

        cevap = self.client.post(reverse('book-delete', args=[self.kitap.pk]))

        self.assertEqual(cevap.status_code, 403)
        self.assertTrue(Book.objects.filter(pk=self.kitap.pk).exists())

    def test_sahibi_silebilir(self):
        self.client.force_login(self.sahip)

        self.client.post(reverse('book-delete', args=[self.kitap.pk]))

        self.assertFalse(Book.objects.filter(pk=self.kitap.pk).exists())

    def test_eklenen_kitabin_sahibi_oturumdaki_kullanicidir(self):
        self.client.force_login(self.baskasi)
        kategori, _ = Category.objects.get_or_create(name='Test Kategorisi')

        self.client.post(reverse('book-create'), {
            'title': 'Yeni Kitap', 'author': 'Y',
            'category': kategori.pk, 'page_count': '50',
        })

        yeni = Book.objects.get(title='Yeni Kitap')
        self.assertEqual(yeni.owner, self.baskasi)


class FavoriTests(TestCase):
    def setUp(self):
        self.kullanici = kullanici_olustur('okur')
        self.kitap = kitap_olustur(self.kullanici)
        self.client.force_login(self.kullanici)

    def test_ayni_kitap_iki_kez_favorilenemez(self):
        Favorite.objects.create(user=self.kullanici, book=self.kitap)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Favorite.objects.create(user=self.kullanici, book=self.kitap)

    def test_butona_ikinci_kez_basmak_favoriden_cikarir(self):
        adres = reverse('favorite-toggle', args=[self.kitap.pk])

        self.client.post(adres)
        self.assertEqual(Favorite.objects.count(), 1)

        self.client.post(adres)
        self.assertEqual(Favorite.objects.count(), 0)

    def test_gorulemeyen_kitap_favorilenemez(self):
        yabanci = kullanici_olustur('yabanci')
        gizli_kitap = kitap_olustur(yabanci, title='Gizli Kitap')

        cevap = self.client.post(reverse('favorite-toggle', args=[gizli_kitap.pk]))

        self.assertEqual(cevap.status_code, 404)
        self.assertEqual(Favorite.objects.count(), 0)


class YorumTests(TestCase):
    def setUp(self):
        self.kitap_sahibi = kullanici_olustur('kitap_sahibi')
        self.yorumcu = kullanici_olustur('yorumcu')
        self.yorumcu.profile.friends.add(self.kitap_sahibi.profile)
        self.kitap = kitap_olustur(self.kitap_sahibi)
        self.yorum = Comment.objects.create(
            book=self.kitap, author=self.yorumcu, text='Güzel kitap.'
        )

    def test_kitap_sahibi_baskasinin_yorumunu_silebilir(self):
        self.client.force_login(self.kitap_sahibi)

        self.client.post(reverse('comment-delete', args=[self.yorum.pk]))

        self.yorum.refresh_from_db()
        self.assertTrue(self.yorum.is_deleted)
        # Soft delete: satır kaldırılmaz, yalnızca işaretlenir.
        self.assertTrue(Comment.objects.filter(pk=self.yorum.pk).exists())
        self.assertEqual(self.yorum.text, 'Güzel kitap.')

    def test_kitap_sahibi_baskasinin_yorumunu_duzenleyemez(self):
        self.client.force_login(self.kitap_sahibi)

        cevap = self.client.get(reverse('comment-update', args=[self.yorum.pk]))

        self.assertEqual(cevap.status_code, 403)

    def test_silinmis_yorum_detay_sayfasinda_gizlenir(self):
        self.yorum.is_deleted = True
        self.yorum.save()
        self.client.force_login(self.yorumcu)

        cevap = self.client.get(reverse('book-detail', args=[self.kitap.pk]))

        icerik = cevap.content.decode()
        self.assertIn('Bu yorum silindi', icerik)
        self.assertNotIn('Güzel kitap.', icerik)
