from django.db import migrations


def assign_owner(apps, schema_editor):
    """Sahipsiz kitapları ilk superuser'a atar.

    owner alanı 0005'te zorunlu hâle getirileceği için bu adım şart:
    sahipsiz tek bir satır kalırsa o migration çalışmaz.
    """
    Book = apps.get_model('books', 'Book')
    User = apps.get_model('auth', 'User')

    sahipsiz = Book.objects.filter(owner__isnull=True)
    if not sahipsiz.exists():
        return

    ilk_superuser = User.objects.filter(is_superuser=True).order_by('pk').first()
    if ilk_superuser is None:
        raise RuntimeError(
            "Sahipsiz kitaplar var ama atanacak bir superuser bulunamadı. "
            "Önce 'manage.py createsuperuser' çalıştırın."
        )

    sahipsiz.update(owner=ilk_superuser)


def clear_owner(apps, schema_editor):
    """Geri alınırsa sahiplikleri temizler.

    Hangi kitabın baştan sahipsiz olduğu bilgisi saklanmadığı için tümü
    temizlenir; bu migration'ın geri alınması yalnızca owner alanı yeniden
    null kabul ettiğinde anlamlıdır.
    """
    Book = apps.get_model('books', 'Book')
    Book.objects.update(owner=None)


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0003_book_owner'),
        ('auth', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(assign_owner, clear_owner),
    ]
