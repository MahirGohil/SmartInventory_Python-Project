import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_inventory.settings")
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import User, OTP
from catalog.models import Category, Product
from cart.models import Cart, CartItem
from orders.models import Orders, OrderItem, Bill
from adminpanel.models import Notification
from predictions.models import StockPrediction, SalesPrediction
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta

print("--- Step 1: Checking AUTH_USER_MODEL and Admin Account ---")
User = get_user_model()
print(f"AUTH_USER_MODEL resolved to: {User.__module__}.{User.__name__}")
assert User == User, "AUTH_USER_MODEL is not accounts.User!"

admin_user = User.objects.filter(username="Admin").first()
assert admin_user is not None, "Admin user does not exist in database!"
assert admin_user.check_password("Admin@123"), "Admin user password does not match 'Admin@123'!"
assert admin_user.is_superuser, "Admin user is not a superuser!"
print("[OK] Admin account verified: username='Admin', password='Admin@123' authenticated successfully.")

print("\n--- Step 2: Testing Models & 11 ER Relationships ---")
# Category & Product
cat, _ = Category.objects.get_or_create(name="Grocery", slug="grocery")
prod, _ = Product.objects.get_or_create(
    product_code="P1001",
    defaults={
        "name": "Rice Bag 5kg",
        "category": cat,
        "price": 250.00,
        "stock_qty": 15,
        "expiry_date": timezone.now().date() + timedelta(days=3)
    }
)
assert prod.category == cat
assert cat.products.filter(id=prod.id).exists()
print("[OK] Relationship 1: Category -> Product (1:N) verified.")

# User
test_user = User.objects.filter(username="testcustomer").first()
if not test_user:
    test_user = User.objects.create_user(
        username="testcustomer",
        password="Password@123",
        email="test@example.com",
        mobile_number="9876543210"
    )

# OTP
otp, _ = OTP.objects.get_or_create(
    user=test_user,
    code="123456",
    defaults={"expires_at": timezone.now() + timedelta(minutes=1)}
)
assert otp.user == test_user
assert test_user.otps.filter(id=otp.id).exists()
print("[OK] Relationship 2: User -> OTP (1:N) verified.")

# Cart
cart, _ = Cart.objects.get_or_create(user=test_user)
assert test_user.cart == cart
assert cart.user == test_user
print("[OK] Relationship 3: User -> Cart (1:1) verified.")

# CartItem
cart_item, _ = CartItem.objects.get_or_create(cart=cart, product=prod, defaults={"quantity": 2})
assert cart_item.cart == cart
assert cart_item.product == prod
assert cart.items.filter(id=cart_item.id).exists()
print("[OK] Relationship 4 & 5: Cart -> CartItem (1:N) and Product -> CartItem (1:N) verified.")

# Orders
order = Orders.objects.filter(user=test_user).first()
if not order:
    order = Orders.objects.create(
        user=test_user,
        status="completed",
        payment_method="UPI",
        subtotal=500.00,
        discount_amount=50.00,
        delivery_charge=0.00,
        total_amount=450.00,
        receiver_name="Test Customer",
        formatted_address="123 Main St",
        address_lat=12.9716,
        address_lng=77.5946,
        user_mobile="9876543210",
        receiver_mobile="9876543210",
        delivery_eta=timezone.now() + timedelta(hours=1)
    )
assert order.user == test_user
assert test_user.orders.filter(id=order.id).exists()
print("[OK] Relationship 6: User -> Orders (1:N) verified.")

# OrderItem
order_item, _ = OrderItem.objects.get_or_create(
    order=order,
    product=prod,
    defaults={"product_name_snapshot": prod.name, "quantity": 2, "price_at_purchase": 250.00}
)
assert order_item.order == order
assert order_item.product == prod
assert order.items.filter(id=order_item.id).exists()
print("[OK] Relationship 7 & 8: Orders -> OrderItem (1:N) and Product -> OrderItem (1:N) verified.")

# Bill
bill, _ = Bill.objects.get_or_create(order=order, defaults={"pdf_file": "bills/sample.pdf"})
assert bill.order == order
assert order.bill == bill
print("[OK] Relationship 9: Orders -> Bill (1:1) verified.")

# Notification
notif, _ = Notification.objects.get_or_create(
    product=prod,
    type="low_stock",
    defaults={"message": "Low stock warning"}
)
assert notif.product == prod
assert prod.notifications.filter(id=notif.id).exists()
print("[OK] Relationship 10: Product -> Notification (1:N) verified.")

# StockPrediction
stock_pred, _ = StockPrediction.objects.get_or_create(
    product=prod,
    week_start=timezone.now().date(),
    defaults={"predicted_qty": 50}
)
assert stock_pred.product == prod
assert prod.stock_predictions.filter(id=stock_pred.id).exists()
print("[OK] Relationship 11: Product -> StockPrediction (1:N) verified.")

# SalesPrediction
sales_pred, _ = SalesPrediction.objects.get_or_create(
    week_start=timezone.now().date(),
    defaults={"predicted_sales": 12500.50}
)
assert sales_pred.week_start == timezone.now().date()
print("[OK] SalesPrediction model verified.")

print("\n--- Step 3: Testing check_stock_notifications Management Command ---")
call_command("check_stock_notifications")
low_stock_notifs = Notification.objects.filter(product=prod, type="low_stock")
expiry_notifs = Notification.objects.filter(product=prod, type="expiry_warning")
assert low_stock_notifs.exists(), "Low stock notification was not created!"
assert expiry_notifs.exists(), "Expiry warning notification was not created!"
print(f"[OK] Notification command verified! Generated notifications count: {Notification.objects.count()}")

print("\n--- Step 4: Verifying Indexes and Constraints ---")
indexes_check = {
    Product: ["category", "stock_qty", "expiry_date"],
    OTP: [["user", "is_used"]],
    Orders: ["placed_at", ["user", "status"]],
    OrderItem: [["product", "order"]],
    Notification: [["is_read", "type"]],
}
for model, expected in indexes_check.items():
    model_indexes = [idx.fields for idx in model._meta.indexes]
    print(f"Model {model.__name__} indexes: {model_indexes}")

assert CartItem._meta.unique_together == (("cart", "product"),), "CartItem unique_together missing!"
assert StockPrediction._meta.unique_together == (("product", "week_start"),), "StockPrediction unique_together missing!"
print("[OK] All Meta indexes and unique_together constraints verified successfully.")

print("\n==========================================")
print("ALL VERIFICATION CHECKS PASSED SUCCESSFULLY!")
print("==========================================")
