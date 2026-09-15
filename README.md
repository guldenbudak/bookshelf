# Kitaplık — Çok Kullanıcılı Sosyal Kitaplık

Kullanıcıların kendi kitaplıklarını oluşturduğu, arkadaşlarının kitaplarını
görebildiği ve yorum yapabildiği bir Django uygulaması. Yeni kayıtlar yönetici
onayından geçmeden uygulamayı kullanamaz.

## Kurulum

```bash
git clone <repo-adresi>
cd bookshelf

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env               # SECRET_KEY ve DEBUG değerlerini düzenle

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Python 3.14 ve Django 6.0 ile geliştirildi.

### .env değişkenleri

| Değişken | Açıklama |
|---|---|
| `SECRET_KEY` | Django imzalama anahtarı. Üretimde gizli tutulmalı. |
| `DEBUG` | `True` / `False`. Üretimde `False` olmalı. |

`.env`, `db.sqlite3` ve `media/` depoya dahil edilmez (`.gitignore`).

## Veri modeli

```
User (django.contrib.auth)
 │
 ├── 1:1 Profile
 │        ├── 1:1 ProfileSettings   tema, gizlilik, bildirim tercihleri
 │        ├── 1:N SocialLink        platform + adres (platform başına bir tane)
 │        └── 1:N Address           ev / iş adresleri, biri varsayılan
 │
 ├── 1:1 AccountApproval      onay durumu + onaylayan admin + tarih
 └── 1:N Book (owner)         [Aşama 4]

Book ──── N:1 Category
```

Sonraki aşamalarda eklenecek tablolar: `FriendRequest`, `Friendship`,
`Favorite`, `Comment`.

### AccountApproval

| Alan | Açıklama |
|---|---|
| `user` | Onayı beklenen kullanıcı (OneToOne) |
| `status` | `pending` / `approved` / `rejected`, varsayılan `pending` |
| `reason` | Özellikle red durumunda kullanıcıya gösterilen sebep |
| `reviewed_by` | İşlemi yapan yönetici (`SET_NULL`) |
| `reviewed_at` | İnceleme zamanı |
| `created_at` | Başvuru zamanı |

`Profile` ve `AccountApproval` kayıtları `post_save` signal'i ile otomatik
oluşturulur (`accounts/signals.py`). Superuser'lar doğrudan `approved` başlar,
aksi hâlde ilk yönetici kendi admin panelinden kilitlenirdi.

## Tamamlanan aşamalar

- [x] **Aşama 0** — Hazırlık
- [x] **Aşama 1** — Kayıt, giriş ve admin onayı
- [x] **Aşama 2** — Profil (çok tablolu)
- [ ] Aşama 3 — Arkadaşlık sistemi
- [ ] Aşama 4 — Kitap sahipliği ve görünürlük
- [ ] Aşama 5 — Favoriler
- [ ] Aşama 6 — Yorumlar
- [ ] Aşama 7 — Kalite ve performans

### Aşama 1'de yapılanlar

| Adres | İşlev |
|---|---|
| `/accounts/register/` | Kayıt. E-posta zorunlu ve benzersiz. |
| `/accounts/login/` | Giriş (Django `LoginView`) |
| `/accounts/logout/` | Çıkış (Django `LogoutView`, yalnızca POST) |
| `/accounts/pending/` | Onay bekleyen / reddedilen kullanıcının durum ekranı |

Kitap view'larının tamamı `@login_required` + `@approved_required` ile
korunmaktadır. Ana sayfa herkese açıktır.

### Aşama 2'de yapılanlar

| Adres | İşlev |
|---|---|
| `/accounts/profile/` | Kendi profilim |
| `/accounts/profile/<username>/` | Başka bir kullanıcının profili |
| `/accounts/profile/edit/` | Profil + ayarlar + sosyal bağlantılar, tek gönderimde |

Onay bekleyen kullanıcı yalnızca **kendi** profilini görebilir; başkasının
profiline giderse `/accounts/pending/` sayfasına yönlendirilir.

Başkasının profilinde kitaplık yalnızca şu durumlarda görünür: profilin
sahibiysen, arkadaşsan (Aşama 3'te bağlanacak) veya profil sahibi
`books_public` ayarını açmışsa. Aksi hâlde "Bu kullanıcının kitaplıklarını
görmek için arkadaş olmalısınız" uyarısı çıkar.

## Tasarım kararları

### Neden `books` app'i yerine ayrı bir `accounts` app'i?

**Sorumluluk ayrımı.** `books` uygulamasının konusu kitaptır; `accounts`
uygulamasının konusu kullanıcıdır (kayıt, onay, profil, arkadaşlık). İkisini
aynı app'te toplamak `models.py` ve `views.py` dosyalarını konusu belirsiz,
uzun dosyalara dönüştürür.

**Taşınabilirlik.** Kayıt ve onay akışı kitaplara özgü değildir. Ayrı bir app
olduğunda başka bir projeye olduğu gibi taşınabilir.

**Django'nun tasarım mantığı.** App, tek bir işi yapan ve kendi modeli,
migration'ı, şablonu ve admin tanımı olan bağımsız birimdir. Django'nun kendi
`django.contrib.auth` uygulaması da aynı ayrımı yapar.

Somut fayda: `accounts` app'inin kendi `migrations/` klasörü olduğu için
kullanıcı tarafındaki şema değişiklikleri kitap tarafındakilerle karışmaz.

### Yetki kontrolü: decorator mı, middleware mi?

Bu projede **decorator** tercih edildi (`accounts/decorators.py`).

| | Decorator | Middleware |
|---|---|---|
| Kapsam | Yalnızca işaretlenen view | Her istek |
| Görünürlük | View'a bakınca korumalı olduğu görülür | View'dan görünmez |
| Yeni view eklenince | Korumasız başlar (unutulabilir) | Otomatik korunur |
| İstisnalar | Gerekmez | Login, register, pending, static, admin için liste tutulmalı |

**Middleware ile yapsaydık ne değişirdi:** kontrol her isteğe otomatik
uygulanırdı, yani yeni bir view yazarken korumayı unutmak imkânsız olurdu —
güvenlik açısından daha güçlü bir varsayılan. Buna karşılık giriş, kayıt ve
onay bekleme sayfalarının kontrolden muaf tutulması gerekirdi; bu muafiyet
listesi büyüdükçe hata yapma ihtimali artar. Ayrıca `book_list` fonksiyonuna
bakan biri, view'ın korumalı olduğunu koddan anlayamazdı.

**Hangisi ne zaman:** korunması gereken view sayısı azsa ve site büyük ölçüde
herkese açıksa decorator uygundur. Sitenin neredeyse tamamı girişe bağlıysa
middleware daha güvenli bir varsayılan sunar. Bu proje şu an ikinci gruba
yaklaşıyor; yine de ödevin gereği ve kodun okunabilirliği nedeniyle decorator
kullanıldı.

Bir ayrıntı: `approved_required` decorator'ı, `@login_required` ile
zincirlenmese bile kendi içinde giriş kontrolü yapar. Anonim kullanıcıda
`request.user.account_approval` çağrısı hata vereceği için bu kontrol
zorunludur.

### Neden `ProfileSettings` ayrı bir tablo? `Profile`'a dört kolon eklenemez miydi?

Eklenebilirdi. `books_public`, `show_email`, `theme` ve `email_notifications`
alanları `Profile` içinde dört kolon olarak da durabilirdi; `SocialLink` ve
`Address`'in aksine bunların sayısı sabit ve her profilde tam bir takım var.

**Ayrı tutmanın avantajı** konu ayrımı. `Profile` "kullanıcı kim" sorusunu
(ad, fotoğraf, tanıtım yazısı), `ProfileSettings` ise "uygulamayı nasıl
kullanmak istiyor" sorusunu (tema, gizlilik) yanıtlıyor. Profil kartını
basarken ayarlara ihtiyaç yoksa o tablo hiç okunmuyor, ve ileride ayar sayısı
arttığında `Profile` tablosu şişmiyor.

**Dezavantajı** maliyeti. İkisini birlikte okumak için iki sorgu gerekiyor ve
düzenleme sayfasında ayrı bir form sınıfı (`ProfileSettingsForm`) yazmak
gerekti — yani kod biraz uzadı.

**Değerlendirme:** bu ölçekte, dört alan için ayrı tablo açmak katı bir
gereklilik değil; `Profile` içinde de durabilirdi ve proje daha kısa olurdu.
Ayrı tablo asıl şu durumlarda karşılığını verir: ayar sayısı büyüdüğünde,
ayarlar profil bilgisinden çok daha nadir okunduğunda, ya da ayarların
sürümlenmesi/önbelleğe alınması gerektiğinde. Bu projede tercih edilmesinin
sebebi ödevin 1:1 ilişki pratiği istemesi ve iki konunun kavramsal olarak
gerçekten ayrı olması.

## Ekran görüntüleri

_Aşama 7'de eklenecek: kayıt, onay bekliyor, profil, arkadaşlar, feed._

## Performans

_Aşama 7'de eklenecek: debug toolbar öncesi/sonrası sorgu sayısı._
