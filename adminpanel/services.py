from datetime import timedelta
from django.utils import timezone
from catalog.models import Product
from adminpanel.models import Notification


def check_product_notifications(product: Product):
    """
    Checks stock level and expiry date for a single Product instance,
    creating, updating, or removing Notification records as appropriate.
    """
    today = timezone.now().date()

    # ── 1. Low Stock Check (<= 20 units) ──────────────────────────────────────
    if product.stock_qty <= 20:
        if product.stock_qty == 0:
            msg = f"Product '{product.name}' is out of stock!"
        else:
            msg = f"{product.name} has only {product.stock_qty} units left."

        notif, created = Notification.objects.get_or_create(
            product=product,
            type="low_stock",
            defaults={"message": msg, "is_read": False},
        )
        if not created:
            # If stock quantity changed (e.g., decreased further or manually updated),
            # update message and mark as unread if the message changed.
            if notif.message != msg:
                notif.message = msg
                notif.is_read = False
                notif.save(update_fields=["message", "is_read"])
    else:
        # Stock replenished above threshold (> 20): remove outdated low_stock alert
        Notification.objects.filter(product=product, type="low_stock").delete()

    # ── 2. Expiry Warning & Expired Checks ───────────────────────────────────
    if product.expiry_date:
        if product.expiry_date <= today:
            # Product has expired
            msg = f"{product.name} has expired on {product.expiry_date.strftime('%b %d, %Y')}."
            # Remove any lingering warning notification
            Notification.objects.filter(product=product, type="expiry_warning").delete()

            notif, created = Notification.objects.get_or_create(
                product=product,
                type="expired",
                defaults={"message": msg, "is_read": False},
            )
            if not created and notif.message != msg:
                notif.message = msg
                notif.save(update_fields=["message"])

        elif product.expiry_date <= today + timedelta(days=7):
            # Expiry warning (expires within 7 days)
            days_left = (product.expiry_date - today).days
            if days_left == 0:
                time_str = "today"
            elif days_left == 1:
                time_str = "tomorrow"
            else:
                time_str = f"in {days_left} days"

            msg = f"{product.name} expires {time_str} ({product.expiry_date.strftime('%b %d, %Y')})."
            # Remove any lingering expired notification if expiry date was extended
            Notification.objects.filter(product=product, type="expired").delete()

            notif, created = Notification.objects.get_or_create(
                product=product,
                type="expiry_warning",
                defaults={"message": msg, "is_read": False},
            )
            if not created and notif.message != msg:
                notif.message = msg
                notif.save(update_fields=["message"])
        else:
            # Expiry date is more than 7 days away: clear any existing expiry alerts
            Notification.objects.filter(
                product=product, type__in=["expiry_warning", "expired"]
            ).delete()
    else:
        # Non-perishable product (no expiry date): clear any existing expiry alerts
        Notification.objects.filter(
            product=product, type__in=["expiry_warning", "expired"]
        ).delete()


def sync_all_notifications():
    """
    Scans all products in the catalog and updates their notification records.
    Returns the total number of unread notifications after syncing.
    """
    for product in Product.objects.all():
        check_product_notifications(product)
