from django.core.management.base import BaseCommand
from accounts.models import User

class Command(BaseCommand):
    help = "Seed initial admin user (Admin / Admin@123)"

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(
            username="Admin",
            defaults={
                "email": "admin@smartinventory.com",
                "mobile_number": "9999999999",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            }
        )
        user.set_password("Admin@123")
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS("Successfully created Admin user."))
        else:
            self.stdout.write(self.style.SUCCESS("Admin user password reset to Admin@123."))
