from django.contrib.auth.models import User
from django.db import models
from django.db.models import Count, Exists, OuterRef, Q
from django.forms import ModelForm


class Category(models.Model):
    name = models.CharField(max_length=50,unique=True)
    def __str__(self):
        return self.name


class BookQuerySet(models.QuerySet):
    """Kitap sorgularının ortak kuralları.

    Görünürlük mantığı view'lara dağılmasın diye burada tanımlı; her view
    aynı kuralı çağırarak kullanıyor.
    """

    def visible_to(self, user):
        """Kullanıcının görmeye yetkili olduğu kitaplar."""
        if not user.is_authenticated:
            return self.none()

        # values_list bir alt sorgu üretir; arkadaş listesi için ayrı bir
        # veritabanı turu atılmaz.
        arkadas_idleri = user.profile.friends.values_list('user_id', flat=True)

        return self.filter(
            Q(owner=user)                                        # kendi kitapları
            | Q(owner_id__in=arkadas_idleri)                     # arkadaşlarınınkiler
            | Q(owner__profile__settings__books_public=True)     # herkese açık olanlar
        )

    def owned_by(self, user):
        """Yalnızca kullanıcının kendi kitapları."""
        if not user.is_authenticated:
            return self.none()
        return self.filter(owner=user)

    def from_friends_of(self, user):
        """Yalnızca arkadaşların kitapları; kendi kitapları hariç."""
        if not user.is_authenticated:
            return self.none()
        arkadas_idleri = user.profile.friends.values_list('user_id', flat=True)
        return self.filter(owner_id__in=arkadas_idleri)

    def favorited_by(self, user):
        """Verilen kullanıcının favorilediği kitaplar."""
        if not user.is_authenticated:
            return self.none()
        return self.filter(favorited_by__user=user)

    def with_related(self):
        """Listelerde N+1 sorguyu önlemek için ilişkili kayıtları da getirir."""
        return self.select_related('category', 'owner')

    def with_favorites(self, user):
        """Her kitaba favori sayısını ve kullanıcının favorileyip
        favorilemediğini ekler — kitap başına ayrı sorgu atmadan."""
        kitaplar = self.annotate(favori_sayisi=Count('favorited_by', distinct=True))

        if not user.is_authenticated:
            return kitaplar

        return kitaplar.annotate(
            favorimde=Exists(
                Favorite.objects.filter(user=user, book=OuterRef('pk'))
            )
        )


class Book(models.Model):
    # Sahiplik üç adımda eklendi: önce null=True (0003), sonra var olan
    # kitaplar ilk superuser'a atandı (0004), en son zorunlu yapıldı (0005).
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='books',
    )
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='books',
    )
    page_count = models.PositiveIntegerField()
    is_read = models.BooleanField(default=False)
    rating = models.PositiveSmallIntegerField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    cover = models.ImageField(upload_to='covers/',blank=True)

    objects = BookQuerySet.as_manager()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            # Aynı kullanıcı aynı kitabı iki kez favorileyemez. Kural
            # veritabanında olduğu için view'daki hata olsa bile aşılamaz.
            models.UniqueConstraint(fields=['user', 'book'], name='uniq_favorite'),
        ]
        verbose_name = "Favori"
        verbose_name_plural = "Favoriler"

    def __str__(self):
        return f"{self.user.username} → {self.book.title}"


class Comment(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField("Yorum", max_length=1000)

    # Yorum silindiğinde satır kaldırılmaz, yalnızca işaretlenir: cevap
    # zinciri kopmasın, moderasyon kaydı kaybolmasın ve gerekirse geri
    # alınabilsin diye. Ekranda "Bu yorum silindi" olarak görünür.
    is_deleted = models.BooleanField("Silindi", default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Yorum"
        verbose_name_plural = "Yorumlar"

    def __str__(self):
        if self.is_deleted:
            return f"{self.author.username} (silinmiş yorum)"
        return f"{self.author.username}: {self.text[:40]}"

    def can_edit(self, user):
        """Yorumu yalnızca yazarı düzenleyebilir."""
        return not self.is_deleted and self.author_id == user.id

    def can_delete(self, user):
        """Yorumu yazarı silebilir; kitabın sahibi de moderasyon için silebilir."""
        if self.is_deleted:
            return False
        return self.author_id == user.id or self.book.owner_id == user.id




