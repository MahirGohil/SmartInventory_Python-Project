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

