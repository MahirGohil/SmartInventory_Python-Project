from django.db import migrations
from django.contrib.auth.hashers import make_password

def seed_admin_user(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    if not User.objects.filter(username="Admin").exists():
        User.objects.create(
            username="Admin",
            password=make_password("Admin@123"),
            email="admin@smartinventory.com",
            mobile_number="9999999999",
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )

def reverse_seed_admin_user(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(username="Admin").delete()

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_admin_user, reverse_seed_admin_user),
    ]
