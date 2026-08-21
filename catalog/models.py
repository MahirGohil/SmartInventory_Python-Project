from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

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

