from django.core.management.base import BaseCommand
from adminpanel.services import sync_all_notifications
from adminpanel.models import Notification


class Command(BaseCommand):
    help = "Check product stock levels and expiry dates, generating notifications as needed."

    def handle(self, *args, **options):
        sync_all_notifications()
        total_count = Notification.objects.count()
        unread_count = Notification.objects.filter(is_read=False).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Finished checking notifications. Total notifications: {total_count} ({unread_count} unread)."
            )
        )
