"""
DEVELOPMENT / TESTING ONLY MANAGEMENT COMMAND

This command generates historical demo data for categories, products, demo users,
orders, and order items across the past 10 weeks to support predictions features.
DO NOT RUN IN PRODUCTION.

Usage:
    python manage.py seed_demo_data
    python manage.py seed_demo_data --clear
"""

import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

from catalog.models import Category, Product
from orders.models import Orders, OrderItem, Bill

User = get_user_model()


class Command(BaseCommand):
    help = "DEVELOPMENT/TEST ONLY: Seed realistic historical order & product data for predictions testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear previously seeded demo data (tagged with 'demo_'/'DEMO_') before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.clear_demo_data()

        self.stdout.write("Starting demo data seeding for predictions testing...")
        categories = self.seed_categories()
        products = self.seed_products(categories)
        users = self.seed_users()
        orders_count = self.seed_orders(users, products)

        self.stdout.write(self.style.SUCCESS(
            f"\n--- SEEDING COMPLETE ---\n"
            f"Total Products in DB: {Product.objects.count()} (Seeded: {len(products)})\n"
            f"Total Users in DB:    {User.objects.count()} (Demo users: {len(users)})\n"
            f"Total Orders in DB:   {Orders.objects.count()} (Seeded: {orders_count})\n"
        ))

    def clear_demo_data(self):
        self.stdout.write("Clearing existing demo data...")
        demo_orders = Orders.objects.filter(user__username__startswith="demo_")
        demo_orders_count = demo_orders.count()
        demo_orders.delete()

        demo_products = Product.objects.filter(product_code__startswith="DEMO_")
        demo_products_count = demo_products.count()
        demo_products.delete()

        demo_users = User.objects.filter(username__startswith="demo_")
        demo_users_count = demo_users.count()
        demo_users.delete()

        self.stdout.write(
            f"Cleared {demo_orders_count} demo orders, {demo_products_count} demo products, {demo_users_count} demo users."
        )

    def seed_categories(self):
        cat_names = ["Grocery", "Snacks", "Electronics", "Makeup"]
        categories = []
        for name in cat_names:
            slug = name.lower()
            cat, _ = Category.objects.get_or_create(name=name, defaults={"slug": slug})
            categories.append(cat)
        return categories

    def seed_products(self, categories):
        cat_dict = {c.name: c for c in categories}
        sample_products = [
            ("DEMO_P01", "Basmati Rice 5kg", "Grocery", 350.00, 45),
            ("DEMO_P02", "Whole Wheat Atta 10kg", "Grocery", 420.00, 30),
            ("DEMO_P03", "Sunflower Oil 1L", "Grocery", 160.00, 60),
            ("DEMO_P04", "Potato Chips 100g", "Snacks", 35.00, 100),
            ("DEMO_P05", "Roasted Cashews 200g", "Snacks", 240.00, 25),
            ("DEMO_P06", "Dark Chocolate 80g", "Snacks", 90.00, 50),
            ("DEMO_P07", "Wireless Earbuds", "Electronics", 1299.00, 15),
            ("DEMO_P08", "USB-C Fast Charger", "Electronics", 499.00, 20),
            ("DEMO_P09", "Power Bank 10000mAh", "Electronics", 999.00, 12),
            ("DEMO_P10", "Matte Lipstick", "Makeup", 399.00, 35),
            ("DEMO_P11", "Hydrating Face Cream", "Makeup", 550.00, 18),
            ("DEMO_P12", "Sunscreen SPF 50", "Makeup", 299.00, 40),
        ]

        products = []
        today = timezone.now().date()
        for code, name, cat_name, price, stock in sample_products:
            prod, _ = Product.objects.get_or_create(
                product_code=code,
                defaults={
                    "name": name,
                    "category": cat_dict[cat_name],
                    "price": price,
                    "stock_qty": stock,
                    "expiry_date": today + timedelta(days=random.randint(15, 180)),
                },
            )
            products.append(prod)
        return products

    def seed_users(self):
        users = []
        for i in range(1, 5):
            username = f"demo_user{i}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"demo_user{i}@example.com",
                    "mobile_number": f"900000000{i}",
                    "is_active": True,
                },
            )
            if created:
                user.set_password("DemoPassword@123")
                user.save()
            users.append(user)
        return users

    def seed_orders(self, users, products):
        now = timezone.now()
        weeks_back = 10
        total_orders_created = 0

        # Generate orders backdated across 10 weeks with a slight upward trend
        for week in range(weeks_back, 0, -1):
            # Base number of orders per week increases slightly closer to current date
            base_orders = 3 + (weeks_back - week)
            orders_this_week = random.randint(base_orders, base_orders + 3)

            for _ in range(orders_this_week):
                user = random.choice(users)
                # Randomize placed_at timestamp within that week
                days_offset = (week * 7) - random.randint(0, 6)
                hours_offset = random.randint(8, 20)
                placed_at = now - timedelta(days=days_offset, hours=hours_offset)

                # Pick 1-4 random products for order items
                selected_products = random.sample(products, k=random.randint(1, 4))
                subtotal = 0
                items_data = []

                for prod in selected_products:
                    qty = random.randint(1, 3)
                    item_price = prod.price
                    subtotal += float(item_price) * qty
                    items_data.append({
                        "product": prod,
                        "name_snapshot": prod.name,
                        "qty": qty,
                        "price": item_price
                    })

                discount = 0.0
                delivery = 0.0 if subtotal >= 200 else 40.0
                total = subtotal - discount + delivery

                order = Orders.objects.create(
                    user=user,
                    status="completed",
                    payment_method=random.choice(["UPI", "COD"]),
                    subtotal=subtotal,
                    discount_amount=discount,
                    delivery_charge=delivery,
                    total_amount=total,
                    receiver_name=f"{user.username.capitalize()}",
                    formatted_address="123 Demo Street, City Center",
                    address_lat=12.971600,
                    address_lng=77.594600,
                    user_mobile=user.mobile_number,
                    receiver_mobile=user.mobile_number,
                    delivery_eta=placed_at + timedelta(hours=1),
                )

                # Override auto_now_add placed_at to historical timestamp
                Orders.objects.filter(id=order.id).update(placed_at=placed_at)
                order.refresh_from_db()

                # Create OrderItems
                for item in items_data:
                    OrderItem.objects.create(
                        order=order,
                        product=item["product"],
                        product_name_snapshot=item["name_snapshot"],
                        quantity=item["qty"],
                        price_at_purchase=item["price"]
                    )

                # Create dummy Bill
                Bill.objects.create(order=order, pdf_file="bills/demo_bill.pdf")
                total_orders_created += 1

        return total_orders_created
