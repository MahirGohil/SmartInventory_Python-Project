# Smart Inventory — Database Structure

Companion to `smart_inventory_spec.md`. Normalized relational design (works on SQLite for dev, PostgreSQL recommended for production because of better date/aggregation functions used by the prediction features).

---

## 1. Entity Overview

| Table | Purpose |
|---|---|
| `User` | Auth + profile (extends Django's `AbstractUser`) |
| `OTP` | Password-reset one-time codes |
| `Category` | Product categories (Grocery, Makeup, Snacks, Electronics, ...) |
| `Product` | Catalog + live stock level |
| `Cart` / `CartItem` | Transient, mutable — "what's currently in the trolley" |
| `Orders` / `OrderItem` | Permanent, immutable snapshot of a completed purchase |
| `Bill` | 1:1 with `Orders` — stores the generated PDF |
| `Notification` | Low-stock / expiry alerts for admin |
| `StockPrediction` | Cached weekly forecast per product |
| `SalesPrediction` | Cached weekly/monthly forecast (store totals, not per-product) |

**Why Cart and Orders are separate tables (not one with a "status" flag):** a cart changes constantly (add/remove/adjust quantity) and has no historical value once checked out. An order is a frozen record — price, quantity, and discount at the moment of purchase must never change even if the product's price changes later. Keeping them separate also keeps prediction queries simple: they only ever read from `Orders`/`OrderItem`, never from `Cart`.

---

## 2. Django Models

```python
# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    mobile_number = models.CharField(max_length=10, unique=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)
    joining_date = models.DateField(auto_now_add=True)
    has_used_first_order_discount = models.BooleanField(default=False)

class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["user", "is_used"])]
```

```python
# catalog/models.py
from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)

class Product(models.Model):
    product_code = models.CharField(max_length=20, unique=True)  # admin-facing "Product ID"
    name = models.CharField(max_length=150)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_qty = models.PositiveIntegerField(default=0)
    photo = models.ImageField(upload_to="products/")
    expiry_date = models.DateField(null=True, blank=True)  # null for non-perishables
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["category"]),
            models.Index(fields=["stock_qty"]),   # speeds up low-stock notification scan
            models.Index(fields=["expiry_date"]), # speeds up expiry-warning scan
        ]
```

```python
# cart/models.py
from django.db import models
from accounts.models import User
from catalog.models import Product

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart")
    updated_at = models.DateTimeField(auto_now=True)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("cart", "product")  # one row per product per cart
```

```python
# orders/models.py
from django.db import models
from accounts.models import User
from catalog.models import Product

class Orders(models.Model):
    STATUS_CHOICES = [("pending", "Pending"), ("completed", "Completed"), ("cancelled", "Cancelled")]
    PAYMENT_CHOICES = [("UPI", "UPI"), ("COD", "COD")]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    payment_method = models.CharField(max_length=5, choices=PAYMENT_CHOICES)

    # snapshot fields — copied at checkout time, never recalculated later
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    # delivery address snapshot (not a live FK to a mutable "Address" table)
    receiver_name = models.CharField(max_length=100)
    formatted_address = models.CharField(max_length=255)
    address_lat = models.DecimalField(max_digits=9, decimal_places=6)
    address_lng = models.DecimalField(max_digits=9, decimal_places=6)
    user_mobile = models.CharField(max_length=10)
    receiver_mobile = models.CharField(max_length=10)

    placed_at = models.DateTimeField(auto_now_add=True)
    delivery_eta = models.DateTimeField()  # randomly generated, 1-2 hrs after placed_at

    class Meta:
        indexes = [
            models.Index(fields=["placed_at"]),   # critical for sales-by-month/week aggregation
            models.Index(fields=["user", "status"]),
        ]

class OrderItem(models.Model):
    order = models.ForeignKey(Orders, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)  # PROTECT: keep history even if product deleted
    product_name_snapshot = models.CharField(max_length=150)  # in case product is later renamed/deleted
    quantity = models.PositiveIntegerField()
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        indexes = [models.Index(fields=["product", "order"])]  # critical for stock-prediction aggregation

class Bill(models.Model):
    order = models.OneToOneField(Orders, on_delete=models.CASCADE, related_name="bill")
    generated_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to="bills/")
```

```python
# adminpanel/models.py
from django.db import models
from catalog.models import Product

class Notification(models.Model):
    TYPE_CHOICES = [
        ("low_stock", "Low stock"),
        ("expiry_warning", "Expiry warning"),
        ("expired", "Product expired"),
    ]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["is_read", "type"])]
```

```python
# predictions/models.py
from django.db import models
from catalog.models import Product

class StockPrediction(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_predictions")
    week_start = models.DateField()
    predicted_qty = models.PositiveIntegerField()
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("product", "week_start")

class SalesPrediction(models.Model):
    week_start = models.DateField(unique=True)
    predicted_sales = models.DecimalField(max_digits=12, decimal_places=2)
    generated_at = models.DateTimeField(auto_now_add=True)
```

---

## 3. Why this shape supports the prediction features cleanly

Both prediction pages need **time-bucketed historical aggregates**. Because `Orders.placed_at` and `OrderItem` are indexed and never mutated after creation, you can aggregate directly with Django's ORM — no separate "analytics" pipeline needed at this scale.

### 3.1 Sales Prediction — data queries

```python
from django.db.models import Sum
from django.db.models.functions import TruncMonth, TruncWeek
from orders.models import Orders

# Graph 1: total sales per month, current year
monthly_sales = (
    Orders.objects.filter(status="completed", placed_at__year=2026)
    .annotate(month=TruncMonth("placed_at"))
    .values("month")
    .annotate(total=Sum("total_amount"))
    .order_by("month")
)

# Graph 2: total sales per week, current month
weekly_sales = (
    Orders.objects.filter(status="completed", placed_at__year=2026, placed_at__month=8)
    .annotate(week=TruncWeek("placed_at"))
    .values("week")
    .annotate(total=Sum("total_amount"))
    .order_by("week")
)
```

The **next-week prediction** is generated from the `weekly_sales` series (e.g. weighted moving average of the last 4-8 weeks, or a lightweight statsmodels/Prophet model once enough history exists) and the result is cached in `SalesPrediction` rather than recomputed on every page view — regenerate via a scheduled Django management command (weekly cron/Celery beat).

### 3.2 Stock Prediction — data queries

```python
from django.db.models import Sum
from django.db.models.functions import TruncWeek
from orders.models import OrderItem

# Weekly demand history per product, most recent N weeks
demand_by_product = (
    OrderItem.objects.filter(order__status="completed")
    .annotate(week=TruncWeek("order__placed_at"))
    .values("product_id", "product_name_snapshot", "week")
    .annotate(qty_sold=Sum("quantity"))
    .order_by("product_id", "week")
)
```

For each product, feed its weekly `qty_sold` series into a simple forecast (moving average is enough initially; upgrade to exponential smoothing once several months of data exist) and write one row per product into `StockPrediction` for the upcoming `week_start`. The Stock Prediction page then just reads `StockPrediction.objects.filter(week_start=upcoming_monday)` — fast, no live computation on page load.

---

## 4. Notification generation (scheduled, not per-request)

Run a daily Django management command (`manage.py check_stock_notifications`) rather than checking on every page load:

```python
from catalog.models import Product
from adminpanel.models import Notification
from django.utils import timezone
from datetime import timedelta

def run():
    today = timezone.now().date()

    for product in Product.objects.filter(stock_qty__lte=20):
        Notification.objects.get_or_create(
            product=product, type="low_stock",
            defaults={"message": f"{product.name} has only {product.stock_qty} units left."}
        )

    for product in Product.objects.filter(expiry_date__lte=today + timedelta(days=7), expiry_date__gt=today):
        Notification.objects.get_or_create(
            product=product, type="expiry_warning",
            defaults={"message": f"{product.name} expires on {product.expiry_date}."}
        )

    for product in Product.objects.filter(expiry_date__lte=today):
        Notification.objects.get_or_create(
            product=product, type="expired",
            defaults={"message": f"{product.name} has expired."}
        )
```

---

## 5. Indexing summary (why each index exists)

| Index | Reason |
|---|---|
| `Product.stock_qty` | Fast low-stock scan for notifications |
| `Product.expiry_date` | Fast expiry scan for notifications |
| `Orders.placed_at` | Backbone of every sales-graph query (month/week grouping) |
| `Orders(user, status)` | Fast "my order history" and first-order-discount check |
| `OrderItem(product, order)` | Backbone of stock-prediction aggregation |
| `Notification(is_read, type)` | Fast "unread notifications" badge query |

---

## 6. First-order discount — recommended implementation

Rather than only trusting a `has_used_first_order_discount` boolean (race conditions on double-submits), check both at the moment of order creation:

```python
def get_discount(user, subtotal):
    already_ordered = Orders.objects.filter(user=user, status="completed").exists()
    if not already_ordered:
        return subtotal * 0.10
    return 0
```

Set `has_used_first_order_discount = True` on the user only after the order is confirmed as `completed`, as a fast-path flag for UI display — but always fall back to the `Orders.objects.filter(...).exists()` check as the source of truth at checkout time.
