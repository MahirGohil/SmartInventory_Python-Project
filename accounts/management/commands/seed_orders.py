import random
from decimal import Decimal
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings

from accounts.models import User
from catalog.models import Product
from orders.models import Orders, OrderItem


FIRST_NAMES = ["Rahul", "Ananya", "Vikram", "Priya", "Sanjay", "Neha", "Rohan", "Kavya", "Aditya", "Sneha"]
LAST_NAMES = ["Sharma", "Patel", "Malhotra", "Nair", "Verma", "Gupta", "Rao", "Joshi", "Singhania", "Deshmukh"]

ADDRESSES = [
    "42 Park Street, Indiranagar, Bengaluru, Karnataka 560038",
    "15 M.G. Road, Bandra West, Mumbai, Maharashtra 400050",
    "88 Jubilee Hills, Hyderabad, Telangana 500033",
    "102 Connaught Place, New Delhi, Delhi 110001",
    "27 Anna Salai, T. Nagar, Chennai, Tamil Nadu 600017",
    "54 Koregaon Park, Pune, Maharashtra 411001",
    "19 Salt Lake Sector V, Kolkata, West Bengal 700091",
]


class Command(BaseCommand):
    help = "Seed realistic historical orders spanning the last 16 weeks for prediction testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete previously seeded dummy orders (where receiver_name starts with 'SEED-').",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            deleted_orders, _ = Orders.objects.filter(receiver_name__startswith="SEED-").delete()
            self.stdout.write(self.style.SUCCESS(f"Successfully cleared {deleted_orders} seeded dummy order records."))
            return

        users = list(User.objects.all())
        if not users:
            self.stdout.write(self.style.ERROR("No users found in database. Please register or seed users first."))
            return

        products = list(Product.objects.select_related("category").all())
        if not products:
            self.stdout.write(self.style.ERROR("No products found in database. Please seed catalog products first."))
            return

        now = timezone.now()
        total_weeks = 16
        start_date = now - timedelta(weeks=total_weeks)

        total_orders_created = 0
        total_items_created = 0
        weekly_summary = []

        # Generate orders week by week
        for week_idx in range(total_weeks):
            week_start = start_date + timedelta(weeks=week_idx)
            week_end = week_start + timedelta(weeks=1)
            week_duration_sec = int((week_end - week_start).total_seconds())

            # Mild upward trend from week 0 to week 15: ~18 base to ~35 base + random variation [-4, 5]
            base_volume = 18 + int(week_idx * 1.1)
            noise = random.randint(-4, 5)
            week_order_count = max(15, min(40, base_volume + noise))

            # Determine product selection weights for this week
            product_weights = []
            for prod in products:
                cat_name = prod.category.name.lower()
                prod_mult = 1.0 + ((prod.id * 7) % 5) * 0.1

                if "grocery" in cat_name:
                    # Steady, high-frequency demand every week
                    w_weight = 10.0 * prod_mult
                elif "snack" in cat_name:
                    # Moderate demand with random weekend/festival spikes on certain weeks
                    is_spike_week = ((week_idx + prod.id) % 4 == 0)
                    w_weight = (14.0 if is_spike_week else 5.0) * prod_mult
                elif "electronic" in cat_name:
                    # Lower frequency, higher value
                    w_weight = 2.2 * prod_mult
                elif "makeup" in cat_name:
                    # Low-to-moderate, steady demand
                    w_weight = 3.8 * prod_mult
                else:
                    w_weight = 5.0 * prod_mult

                product_weights.append(max(0.1, w_weight))

            week_created_orders = 0

            for _ in range(week_order_count):
                user = random.choice(users)

                # Random timestamp in the week
                offset_sec = random.randint(0, week_duration_sec - 1)
                placed_at = week_start + timedelta(seconds=offset_sec)
                delivery_eta = placed_at + timedelta(minutes=random.randint(60, 120))

                # Pick 1 to 4 distinct products based on weights
                num_items = min(random.randint(1, 4), len(products))
                chosen_products = random.choices(products, weights=product_weights, k=num_items * 2)
                # Deduplicate while preserving weighted selection order
                selected_products = []
                for p in chosen_products:
                    if p not in selected_products:
                        selected_products.append(p)
                    if len(selected_products) == num_items:
                        break

                # Prepare items & totals
                order_items_data = []
                subtotal = Decimal("0.00")

                for prod in selected_products:
                    qty = random.randint(1, 5)
                    price = prod.price
                    subtotal += price * qty
                    order_items_data.append({
                        "product": prod,
                        "product_name_snapshot": prod.name,
                        "quantity": qty,
                        "price_at_purchase": price,
                    })

                # Calculate delivery charge per business logic
                delivery_charge_setting = getattr(settings, "DELIVERY_CHARGE", Decimal("40.00"))
                delivery_charge = Decimal("0.00") if subtotal >= Decimal("200.00") else Decimal(str(delivery_charge_setting))
                discount_amount = Decimal("0.00")
                total_amount = subtotal - discount_amount + delivery_charge

                receiver_name = f"SEED-{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
                formatted_addr = random.choice(ADDRESSES)
                lat = Decimal(f"{12.971598 + random.uniform(-0.05, 0.05):.6f}")
                lng = Decimal(f"{77.594562 + random.uniform(-0.05, 0.05):.6f}")
                u_mobile = user.mobile_number if (user.mobile_number and len(user.mobile_number) == 10) else f"98{random.randint(10000078, 99999999)}"
                r_mobile = f"98{random.randint(10000078, 99999999)}"

                # Create Order (initially gets auto_now_add placed_at)
                order = Orders.objects.create(
                    user=user,
                    status="completed",
                    payment_method=random.choice(["UPI", "COD"]),
                    subtotal=subtotal,
                    discount_amount=discount_amount,
                    delivery_charge=delivery_charge,
                    total_amount=total_amount,
                    receiver_name=receiver_name,
                    formatted_address=formatted_addr,
                    address_lat=lat,
                    address_lng=lng,
                    user_mobile=u_mobile,
                    receiver_mobile=r_mobile,
                    delivery_eta=delivery_eta,
                )

                # Requirement 2: Bulk update placed_at to bypass auto_now_add=True
                Orders.objects.filter(id=order.id).update(placed_at=placed_at)

                # Create OrderItems
                for item_data in order_items_data:
                    OrderItem.objects.create(
                        order=order,
                        product=item_data["product"],
                        product_name_snapshot=item_data["product_name_snapshot"],
                        quantity=item_data["quantity"],
                        price_at_purchase=item_data["price_at_purchase"],
                    )
                    total_items_created += 1

                week_created_orders += 1
                total_orders_created += 1

            weekly_summary.append((week_start.strftime("%Y-%m-%d"), week_end.strftime("%Y-%m-%d"), week_created_orders))

        # Output Summary
        self.stdout.write(self.style.SUCCESS("\n================ SEED ORDERS SUMMARY ================"))
        self.stdout.write(f"Total Orders Created:      {total_orders_created}")
        self.stdout.write(f"Total Order Items Created: {total_items_created}")
        self.stdout.write(f"Date Range Covered:        {start_date.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}")
        self.stdout.write("-----------------------------------------------------")
        self.stdout.write("Weekly Order Breakdown:")
        for w_start, w_end, count in weekly_summary:
            self.stdout.write(f"  Week {w_start} ~ {w_end}: {count} orders")
        self.stdout.write(self.style.SUCCESS("=====================================================\n"))
