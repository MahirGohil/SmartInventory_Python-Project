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

