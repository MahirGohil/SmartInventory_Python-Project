from django.contrib import admin
from catalog.models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("product_code", "name", "category", "price", "stock_qty", "expiry_date", "created_at")
    list_filter = ("category", "expiry_date")
    search_fields = ("name", "product_code")
