from django.db import migrations


def create_missing_settings(apps, schema_editor):
    """ProfileSettings tablosundan önce oluşmuş profillere ayar kaydı ekler."""
    Profile = apps.get_model('accounts', 'Profile')
    ProfileSettings = apps.get_model('accounts', 'ProfileSettings')

    eksik = Profile.objects.filter(settings__isnull=True)
    ProfileSettings.objects.bulk_create(
        [ProfileSettings(profile=profile) for profile in eksik]
    )


def delete_created_settings(apps, schema_editor):
    """Geri alınırsa ayar kayıtlarını siler."""
    ProfileSettings = apps.get_model('accounts', 'ProfileSettings')
    ProfileSettings.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_profile_avatar_profile_bio_profile_birth_date_and_more'),
    ]

    operations = [
        migrations.RunPython(create_missing_settings, delete_created_settings),
    ]
