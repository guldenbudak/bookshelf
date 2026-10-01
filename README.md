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
 ├── 1:N Book (owner)         kitabın sahibi, zorunlu
 ├── 1:N Favorite            kullanıcı + kitap (çift başına tek kayıt)
 └── 1:N Comment             yorum; silinince satır kalır, işaretlenir

Book ──── N:1 Category
```

Tüm tablolar eklendi.

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
- [x] **Aşama 3** — Arkadaşlık sistemi
- [x] **Aşama 4** — Kitap sahipliği ve görünürlük
- [x] **Aşama 5** — Favoriler
- [x] **Aşama 6** — Yorumlar
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
sahibiysen, arkadaşsan veya profil sahibi `books_public` ayarını açmışsa.
Aksi hâlde "Bu kullanıcının kitaplıklarını görmek için arkadaş olmalısınız"
uyarısı çıkar.

### Aşama 3'te yapılanlar

| Adres | Yöntem | İşlev |
|---|---|---|
| `/accounts/friends/` | GET | Arkadaşlar, gelen ve gönderilen istekler (sekmeli) |
| `/accounts/users/?q=` | GET | Kullanıcı arama |
| `/accounts/friends/request/<username>/` | POST | İstek gönder |
| `/accounts/friends/accept/<pk>/` | POST | İsteği kabul et |
| `/accounts/friends/reject/<pk>/` | POST | İsteği reddet |
| `/accounts/friends/remove/<username>/` | POST | Arkadaşlıktan çıkar |

Durum değiştiren dört işlem yalnızca POST kabul eder (`@require_POST`); GET
ile çağrıldıklarında 405 dönerler.

### Aşama 4'te yapılanlar

Her kitabın artık zorunlu bir sahibi var (`Book.owner`). Alan üç migration'da
eklendi; ayrıntısı aşağıda.

| Adres | İçerik |
|---|---|
| `/books/` | Kullanıcının kendi kitapları |
| `/feed/` | Arkadaşlarının kitapları |
| `/books/<pk>/` | Yalnızca görme yetkisi varsa; yoksa 404 |

Görünürlük kuralı `BookQuerySet` içinde tanımlı, view'lara dağıtılmadı:

| Bakan kişi | Sonuç |
|---|---|
| Kitabın sahibi | Görür |
| Sahibin arkadaşı | Görür |
| Sahip kitaplığını herkese açmışsa | Görür |
| Diğerleri | 404 |
| Giriş yapmamış | Giriş sayfasına yönlendirilir |

Güncelleme ve silme yalnızca sahibine açıktır; başkası denerse 403 döner.
Kitap eklerken sahip formdan değil oturumdaki kullanıcıdan alınır, böylece
kimse başkasının adına kitap kaydedemez.

### Aşama 5'te yapılanlar

| Adres | Yöntem | İşlev |
|---|---|---|
| `/favorites/` | GET | Kullanıcının favorileri |
| `/books/<pk>/favorite/` | POST | Favoriye ekler, zaten favorideyse çıkarır |

Kullanıcı **görebildiği** her kitabı favorileyebilir; sahibi olması gerekmez.
Göremediği bir kitabın adresini denerse 404 alır. Aynı kitap iki kez
favorilenemez: `Favorite` tablosunda `user` + `book` çifti için tekillik
kısıtı var, view ise `get_or_create` ile aynı butonu aç/kapa düğmesine
çeviriyor.

Kitap kartlarında favori sayısı ve kullanıcının kendi durumu `annotate` ile
ana sorguya ekleniyor, kart başına sorgu atılmıyor.

Bir kullanıcının favorileri profilinde, kitaplıkla aynı kurala tabi olarak
görünür: sahibi, arkadaşı veya `books_public` açıksa herkes.

### Aşama 6'da yapılanlar

| Adres | Yöntem | İşlev |
|---|---|---|
| `/books/<pk>/comment/` | POST | Yorum ekler |
| `/comments/<pk>/edit/` | GET/POST | Yorumu düzenler |
| `/comments/<pk>/delete/` | POST | Yorumu siler (işaretler) |

Yorumlar kitap detayında, en yeniden eskiye, yazarın avatarı ve tarihiyle
listelenir. Düzenlenen yorumlarda tarihin yanında "düzenlendi" notu çıkar.

Yetkiler ikiye ayrılır:

| | Düzenleyebilir | Silebilir |
|---|---|---|
| Yorumun yazarı | ✓ | ✓ |
| Kitabın sahibi | ✗ | ✓ (moderasyon) |
| Diğerleri | ✗ | ✗ |

Yorum yazmak için kitabı görebiliyor olmak yeterlidir; sahibi olmak
gerekmez. Yorum düzenleme ve silme adresleri de kitabı `visible_to` içinde
arar, böylece görünürlük zinciri yorumlarda delinmez.

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

### Arkadaşlık: simetriyi nasıl sakladık?

Arkadaşlık simetriktir — A ile B arkadaşsa B ile A da arkadaştır. Bunu
saklamanın iki yolu var:

| | Tek satır (A, B) | İki satır (A→B ve B→A) |
|---|---|---|
| "Arkadaşlarım kimler?" sorgusu | İki sütunu da taramak gerekir | Tek sütun, basit |
| Veri tekrarı | Yok | Var |
| Tutarsızlık riski | Yok | Biri silinip diğeri kalabilir |

Django'nun `ManyToManyField('self', symmetrical=True)` alanını kullandık.
Kaynak koduna bakıldığında görülüyor ki Django `add()` çağrıldığında ters
yöndeki satırı da kendisi ekliyor, `remove()` çağrıldığında ikisini de
siliyor. Yani veritabanında **iki satır** tutuluyor ama senkronizasyonu
framework üstleniyor: sorgu tarafında iki satırın basitliği, tutarsızlık
riski olmadan elde ediliyor. View'larda tek bir çağrı yetiyor:

```python
request.user.profile.friends.add(other.profile)     # iki yön de kurulur
request.user.profile.friends.remove(other.profile)  # iki yön de biter
```

### A ve B aynı anda birbirine istek gönderirse?

`FriendRequest` tablosunda yön bilgisi olduğu için A→B ve B→A **ayrı
satırlardır**; veritabanı ikisine de izin verir. Karar view'da verildi:
ikinci istek gönderilirken karşı taraftan bekleyen bir istek varsa, ikinci
bir istek açmak yerine **ikisi doğrudan arkadaş yapılır** ve var olan istek
`accepted` olarak kapatılır.

Gerekçe: iki taraf da aynı şeyi istediğini zaten beyan etmiştir, fazladan
bir onay adımı istemek gereksizdir. Yaygın sosyal uygulamalar da böyle
davranır.

### Kendine istek gönderilemez

İki katmanda engellendi:

- **Veritabanı:** `CheckConstraint(condition=~Q(from_user=F('to_user')))`.
  Kod hatası, admin paneli veya elle SQL dahil hiçbir yoldan aşılamaz.
- **View:** gönderen ile alıcı aynıysa işlem yapılmadan anlaşılır bir mesaj
  gösterilir.

İkincisi olmasaydı kullanıcı, veritabanı hatasını ham bir `IntegrityError`
sayfası olarak görürdü. Birincisi olmasaydı koruma yalnızca uygulamanın
doğru yazıldığı varsayımına dayanırdı.

Arayüzde ayrıca kendi profilinde "Arkadaş ekle" butonu gösterilmiyor; ancak
bu güvenlik değil, yalnızca kullanıcı deneyimidir — asıl kontrol yukarıdaki
iki katmandadır.

### Zaten arkadaş olana tekrar istek gönderilemez

`friend_request_send` işleme başlamadan önce `is_friend_with()` ile kontrol
eder ve "zaten arkadaşsınız" mesajıyla döner. Ayrıca arayüz bu durumda
"Arkadaş ekle" yerine "Arkadaşlıktan çıkar" butonunu gösterir.

### Reddedilen istek tekrar gönderilebilir mi?

**Evet.** Gerekçe: red çoğu zaman kalıcı bir karar değildir; yanlışlıkla
reddedilmiş olabilir ya da taraflar arasındaki durum değişmiş olabilir.
Kalıcı engelleme istenirse bu ayrı bir "engelleme" özelliği olarak
tasarlanmalıdır, reddedilen isteğin yan etkisi olarak değil.

Teknik sonucu: `UniqueConstraint(from_user, to_user)` bir yön için yalnızca
tek satıra izin verdiğinden, tekrar gönderimde yeni satır açılamaz. Bunun
yerine var olan satırın durumu `pending`'e geri alınır:

```python
istek, yeni_mi = FriendRequest.objects.get_or_create(...)
if not yeni_mi and istek.status != PENDING:
    istek.status = PENDING
    istek.save()
```

Aynı mekanizma arkadaşlıktan çıkıp yeniden istek gönderme durumunu da
kapsar; bu yüzden `friend_remove`, geride kalan `accepted` satırını
`rejected` olarak kapatır ve kayıt gerçek durumla uyumlu kalır.

### İsteği yalnızca alıcısı cevaplayabilir

Kabul ve reddetme view'ları isteği ararken alıcıyı da sorguya dahil eder:

```python
get_object_or_404(FriendRequest, pk=pk, to_user=request.user, status=PENDING)
```

Kontrolün ayrı bir `if` yerine sorgunun içinde olması bilinçlidir: yetki
kontrolünü yazmayı unutmak mümkün değildir, çünkü kayıt zaten yalnızca
yetkili kullanıcı için bulunur. Başkasının isteğine müdahale eden veya
kendi gönderdiği isteği kabul etmeye çalışan kullanıcı 404 alır.

### Tekrarlanan sorgular

`Profile.get_friends()` arkadaş listesini `select_related('user')` ile
getirir; arkadaşlar ve istek listelerinde ilişkili kullanıcı ve profil
kayıtları da tek sorguda çekilir. Kullanıcı aramasında ilişki durumu her
satır için ayrı ayrı sorgulanmaz, üç küme (arkadaşlar, gönderilen istekler,
gelen istekler) baştan birer sorguyla alınıp şablonda karşılaştırılır.

### Yetkisiz erişimde neden 403 yerine 404?

**403 bir bilgi sızdırır: kaydın var olduğu.** "Böyle bir şey var ama sen
giremezsin" demek, aslında o şeyin varlığını doğrulamaktır.

Bir saldırgan adresleri sırayla deneyerek bundan yararlanabilir:

```
/books/1/  → 403   (var)
/books/2/  → 404   (yok)
/books/3/  → 403   (var)
```

Hiçbir kitabı göremediği hâlde hangi numaraların dolu olduğunu öğrenir. Buna
numara tarama (enumeration) denir. Kitap sayısını öğrenmek tek başına zararsız
görünebilir; ama aynı yöntem `/users/<ad>/` üzerinde kullanıcı adı doğrulamaya,
`/orders/<no>/` üzerinde sipariş hacmi tahminine dönüşür.

404 bu farkı ortadan kaldırır: yetkisi olmayan kullanıcı için kayıt "yok"
sayılır, var olup olmadığı anlaşılamaz.

**Bedeli** kullanıcı deneyimidir. Gerçekten yetkili olan ama oturumu düşmüş bir
kullanıcı "sayfa bulunamadı" görür ve nedenini anlayamaz. 403 ise "yetkin yok,
yöneticinden iste" gibi yol gösterici bir cevaptır.

**Bu projedeki tercih:** kitap detayında 404 kullanıldı, çünkü yabancı bir
kullanıcının bir kitabın varlığını bile öğrenmemesi gerekir. Güncelleme ve
silmede ödevin isteği doğrultusunda 403 kullanıldı; oradaki sızıntı sınırlıdır,
zira o adrese ulaşabilmek için zaten giriş yapmış ve onaylanmış olmak gerekir.

Genel kural: **kaydın varlığı da gizliyse 404, yalnızca erişim yetkisi eksikse
403.**

### Sahiplik alanı neden üç migration'da eklendi?

`Book.owner` zorunlu (`null=False`) bir alan, ama tabloda zaten dokuz sahipsiz
kitap vardı. Alanı tek adımda zorunlu olarak eklemek mümkün değil: veritabanı
mevcut satırlara ne yazacağını bilemez ve işlem durur.

| Migration | Ne yapar |
|---|---|
| `0003_book_owner` | Alanı `null=True` ile ekler |
| `0004_assign_existing_books_to_first_superuser` | Sahipsiz kitapları ilk superuser'a atar (`RunPython`) |
| `0005_alter_book_owner` | Alanı `null=False` yapar |

Veri taşıyan adım `apps.get_model()` kullanır, doğrudan `import` etmez: migration
gelecekte de çalışacağı için modelin bugünkü hâline değil, o migration anındaki
hâline ihtiyaç duyar. Ayrıca `reverse_code` tanımlıdır, yani adım geri alınabilir;
atanacak kitap yoksa erken çıkar, böylece boş bir veritabanında da sorunsuz
çalışır.

### Arkadaşlıktan çıkınca favorideki kitap ne olmalı?

**Karar: favori kaydı silinmez.** Kitap listede "erişilemiyor" kartı olarak
kalır; adı, yazarı ve kapağı gösterilmez. Arkadaşlık yeniden kurulursa kart
kendiliğinden normale döner, çünkü kayıt zaten yerindedir.

**Gerekçe.** Favori, kullanıcının kendi verisidir — o kitabı o beğenip
listesine eklemiştir. Arkadaşlık ise ayrı bir ilişkidir. "Arkadaşlıktan
çıkar" düğmesine basan kişi favorilerinin de silineceğini beklemez; bir
işlemin ilgisiz başka bir veriyi yok etmesi sürpriz ve geri dönüşsüz olur.
Arkadaşlıklar ayrıca geçicidir, yanlışlıkla da bozulabilir; her seferinde
favorilerin sıfırlanması gereksiz bir kayıptır.

**Neden sessizce gizlemek yerine kart gösteriliyor.** Kullanıcı kendi
sayfasında "12 favorim vardı, şimdi 10 görünüyor" durumuyla karşılaşmamalı.
Görünür bir açıklama, sessiz bir eksilmeden daha dürüsttür.

**Neden kitabın adı bile yazmıyor.** Sahibiyle arkadaşlık bittiği an o
kitabın içeriğine erişim hakkı da biter; başlık da içeriğin parçasıdır.
Kart yalnızca "burada erişemediğin bir kayıt var" der.

### Başkasının profilinde favoriler nasıl süzülüyor?

Profil sahibinin favorileri, **ziyaretçinin de görmeye yetkili olduğu**
kitaplarla sınırlanır:

```python
Book.objects.favorited_by(profile_user).visible_to(request.user)
```

İkinci süzgeç olmasaydı favoriler bir arka kapıya dönüşürdü: Ayşe ile
arkadaş olmak, Ayşe'nin favorilediği herkesin kitabını görmeye yeterdi.

Bu listede erişilemeyen kayıtlar için yer tutucu **gösterilmez** — kendi
favori sayfasındakinin aksine. Aradaki fark şu: kendi sayfanda o kayıtlar
senin verindir ve eksilmeyi açıklamak gerekir; başkasının profilinde ise
sana ait olmayan kayıtların sayısını duyurmak yalnızca bilgi sızdırır.

### Yorumlar neden gerçekten silinmiyor (soft delete)?

Silme isteği satırı kaldırmaz; yalnızca `is_deleted` alanını işaretler.
Ekranda "Bu yorum silindi" yazar, metin ve yazar bilgisi gösterilmez ama
kayıt veritabanında durur.

**Konuşmanın akışı bozulmasın.** Bir yoruma cevap verilmişse ve ana yorum
gerçekten silinirse, cevap kime verildiği belirsiz bir şekilde havada
kalır. Yer tutucu bırakmak bağlamı korur. (Cevap özelliği bu projede yok
ama model buna hazır olacak şekilde kuruldu.)

**Moderasyon izlenebilir olsun.** Kitap sahibi başkasının yorumunu
silebiliyor. Kayıt tamamen yok edilseydi "burada ne yazıyordu, haklı bir
silme miydi?" sorusunun cevabı kalmazdı.

**Geri alınabilir olsun.** Yanlışlıkla silinen bir yorum `is_deleted`
alanı kapatılarak geri getirilebilir; `delete()` çağrılsaydı bu mümkün
olmazdı.

Silinmiş yorum tekrar silinemez ve düzenlenemez: `can_edit` ve
`can_delete` metotları `is_deleted` işaretli kayıtlar için `False` döner,
böylece butona iki kez basılması veya adresin elle çağrılması bir şeyi
değiştirmez.

### Kitap sahibi neden silebiliyor ama düzenleyemiyor?

Moderasyon yetkisi "bu içeriği kaldır" demektir, "bu içeriği değiştir"
demek değil. Kitap sahibi kendi kitabının altındaki uygunsuz bir yorumu
kaldırabilmeli; ama başkasının cümlesini değiştirip onun adı altında
bırakabilmesi, yorumun yazarına atfedilen sözü tahrif etmek olurdu.

Bu yüzden iki ayrı metot var:

```python
can_edit(user)    → yalnızca yazarı
can_delete(user)  → yazarı veya kitabın sahibi
```

### Yazar ve kitap neden formda değil?

`CommentForm` yalnızca `text` alanını içerir. `author` ve `book`
oturumdan ve adresten alınır.

Formdaki her alan tarayıcıdan gelir ve kullanıcı tarayıcıyı kontrol eder:
açılır listedeki değeri geliştirici araçlarıyla değiştirebilir, ya da
formu hiç kullanmayıp isteği doğrudan gönderebilir. `author` formda
olsaydı, bir kullanıcı başkasının adına yorum yazabilirdi. Gizli alan
(`type="hidden"`) da çözüm değildir: gizli, "görünmez" demektir,
"değiştirilemez" değil.

Aynı kural `BookForm`'daki `owner` ve arkadaşlık isteğindeki `from_user`
için de geçerlidir: **kullanıcının belirlememesi gereken alan forma
konmaz, sunucu kendi belirler.**

## Ekran görüntüleri

_Aşama 7'de eklenecek: kayıt, onay bekliyor, profil, arkadaşlar, feed._

## Performans

_Aşama 7'de eklenecek: debug toolbar öncesi/sonrası sorgu sayısı._
