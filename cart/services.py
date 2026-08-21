import random
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from cart.models import Cart, CartItem
from catalog.models import Product

# Read delivery charge from settings (configured via DELIVERY_CHARGE in .env).
# BUG 5 FIX: Previously hard-coded as Decimal("40.00") locally, which meant
# changing DELIVERY_CHARGE in .env had no effect whatsoever.
DELIVERY_CHARGE = Decimal(str(settings.DELIVERY_CHARGE))
FREE_DELIVERY_THRESHOLD = Decimal("200.00")
FIRST_ORDER_DISCOUNT_PERCENT = Decimal("0.10")

from orders.models import Orders


def get_or_create_cart(user):
    """Returns the Cart instance for the user, creating one if it doesn't exist."""
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def calculate_totals(cart):
    """
    Calculates subtotal, first-order discount, delivery charge, and final total for a cart.

    Returns dict:
        {
            'subtotal': Decimal,
            'discount_amount': Decimal,
            'is_first_order': bool,
            'delivery_charge': Decimal,
            'is_free_delivery': bool,
            'total_amount': Decimal,
            'item_count': int,
        }
    """
    items = cart.items.select_related("product").all()
    subtotal = Decimal("0.00")
    item_count = 0

    for item in items:
        subtotal += item.product.price * item.quantity
        item_count += item.quantity

    # First-order discount logic (10% off subtotal if user has no completed orders)
    is_first_order = False
    discount_amount = Decimal("0.00")
    if subtotal > 0 and cart.user:
        already_ordered = Orders.objects.filter(user=cart.user, status="completed").exists()
        if not already_ordered:
            is_first_order = True
            discount_amount = (subtotal * FIRST_ORDER_DISCOUNT_PERCENT).quantize(Decimal("0.01"))

    # Delivery charge logic (Free if subtotal >= 200, else fixed 40 INR)
    is_free_delivery = subtotal >= FREE_DELIVERY_THRESHOLD or subtotal == 0
    if is_free_delivery:
        delivery_charge = Decimal("0.00")
    else:
        delivery_charge = DELIVERY_CHARGE

    total_amount = subtotal - discount_amount + delivery_charge

    return {
        "subtotal": subtotal,
        "discount_amount": discount_amount,
        "is_first_order": is_first_order,
        "delivery_charge": delivery_charge,
        "is_free_delivery": is_free_delivery,
        "total_amount": total_amount,
        "item_count": item_count,
    }


def get_or_generate_delivery_eta(request):
    """
    Generates a consistent estimated delivery time (random 1-2 hours after current time)
    and stores it in the user's session (`delivery_eta`).

    Reuses the session value on repeat calls until the cart is cleared/placed.
    Invalidates the cached ETA if it has already passed (stale session).
    """
    eta_str = request.session.get("delivery_eta")
    if eta_str:
        try:
            cached_eta = timezone.datetime.fromisoformat(eta_str)
            # Ensure it's timezone-aware (older sessions may have stored naive datetimes)
            if timezone.is_naive(cached_eta):
                cached_eta = timezone.make_aware(cached_eta)
            # Only reuse if ETA is still in the future
            if cached_eta > timezone.now():
                return cached_eta
        except (ValueError, TypeError):
            pass
        # Clear stale or invalid cached ETA
        del request.session["delivery_eta"]

    # Generate random 1 to 2 hours in the future
    random_minutes = random.randint(60, 120)
    eta_dt = timezone.now() + timedelta(minutes=random_minutes)

    # Store ISO formatted string in session
    request.session["delivery_eta"] = eta_dt.isoformat()
    return eta_dt
