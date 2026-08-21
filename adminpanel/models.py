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

