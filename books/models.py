from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
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

    def with_related(self):
        """Listelerde N+1 sorguyu önlemek için ilişkili kayıtları da getirir."""
        return self.select_related('category', 'owner')


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




