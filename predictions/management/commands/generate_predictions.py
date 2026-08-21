"""
DEVELOPMENT/ADMIN command — safe to re-run in any environment.

Calls forecast_next_week_sales() and forecast_stock_needs(), then writes
results into SalesPrediction and StockPrediction using update_or_create on
their unique constraints (week_start / product+week_start) so re-running
never creates duplicates.

Usage:
    python manage.py generate_predictions
"""

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from predictions.models import SalesPrediction, StockPrediction
from predictions.services import (
    get_weekly_sales,
    forecast_next_week_sales,
    forecast_stock_needs,
)
from catalog.models import Product


class Command(BaseCommand):
    help = "Generate and cache next-week sales and stock predictions. Safe to re-run."

    def handle(self, *args, **options):
        now = timezone.now()
        today = now.date()

        # Next week's Monday (ISO week start)
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_week_start = today + timedelta(days=days_until_monday)

        self.stdout.write(f"Generating predictions for week starting {next_week_start} ...")

        # ── Sales Prediction ──────────────────────────────────────────────────
        weekly_sales = get_weekly_sales(now.year, now.month)
        predicted_sales = forecast_next_week_sales(weekly_sales)

        sp_obj, sp_created = SalesPrediction.objects.update_or_create(
            week_start=next_week_start,
            defaults={"predicted_sales": predicted_sales},
        )
        action = "Created" if sp_created else "Updated"
        self.stdout.write(
            f"  {action} SalesPrediction: INR {predicted_sales} for week {next_week_start}"
        )

        # ── Stock Prediction ──────────────────────────────────────────────────
        stock_forecasts = forecast_stock_needs()
        stock_created = 0
        stock_updated = 0

        for item in stock_forecasts:
            try:
                product = Product.objects.get(id=item["product_id"])
            except Product.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"  Skipping product #{item['product_id']} - not found")
                )
                continue

            _, created = StockPrediction.objects.update_or_create(
                product=product,
                week_start=next_week_start,
                defaults={"predicted_qty": item["predicted_qty"]},
            )
            if created:
                stock_created += 1
            else:
                stock_updated += 1

        self.stdout.write(
            f"  StockPredictions: {stock_created} created, {stock_updated} updated "
            f"({len(stock_forecasts)} products total)"
        )
        self.stdout.write(self.style.SUCCESS("Predictions generation complete."))
