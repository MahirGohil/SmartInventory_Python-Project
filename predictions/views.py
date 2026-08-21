import functools
from datetime import timedelta
from django.shortcuts import render, redirect
from django.utils import timezone

from predictions.models import SalesPrediction, StockPrediction
from predictions.services import (
    get_monthly_sales,
    get_weekly_sales,
    forecast_next_week_sales,
    forecast_stock_needs,
)


def admin_required(view_func):
    """Restrict to superusers; redirect others to the shop page."""
    # BUG 4 FIX: Added @functools.wraps so wrapped views retain their __name__,
    # __doc__, and other attributes — required for Django URL reversing and
    # introspection tools to work correctly.
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if not request.user.is_superuser:
            return redirect("catalog:shop")
        return view_func(request, *args, **kwargs)
    return wrapper


def _get_next_week_start():
    """Returns next Monday's date (ISO week start)."""
    today = timezone.now().date()
    days_until_monday = (7 - today.weekday()) % 7 or 7
    return today + timedelta(days=days_until_monday)


@admin_required
def sales_prediction_page(request):
    """
    Renders:
    - Monthly sales bar chart (Chart.js) for the current year.
    - Weekly sales line chart for the current month.
    - Predicted sales for next week (cached SalesPrediction or inline fallback).
    """
    now = timezone.now()
    year = now.year
    month = now.month

    monthly_sales = get_monthly_sales(year)
    weekly_sales = get_weekly_sales(year, month)
    next_week_start = _get_next_week_start()

    # Try cached prediction first
    try:
        cached = SalesPrediction.objects.get(week_start=next_week_start)
        predicted_sales = float(cached.predicted_sales)
        prediction_source = "cached"
    except SalesPrediction.DoesNotExist:
        # Inline fallback: compute and save so next load is instant
        predicted_sales = forecast_next_week_sales(weekly_sales)
        if predicted_sales > 0:
            SalesPrediction.objects.update_or_create(
                week_start=next_week_start,
                defaults={"predicted_sales": predicted_sales},
            )
        prediction_source = "live"

    # BUG 1 FIX: Compute data-presence flags so the template can show a proper
    # empty-state banner instead of a blank/zero chart when there is no data.
    has_monthly_data = any(row["total"] > 0 for row in monthly_sales)
    has_weekly_data = len(weekly_sales) > 0

    context = {
        "year": year,
        "month": now.strftime("%B"),
        "monthly_sales": monthly_sales,
        "monthly_labels": [row["label"] for row in monthly_sales],
        "monthly_totals": [row["total"] for row in monthly_sales],
        "weekly_sales": weekly_sales,
        "weekly_labels": [row["label"] for row in weekly_sales],
        "weekly_totals": [row["total"] for row in weekly_sales],
        "predicted_sales": predicted_sales,
        "next_week_start": next_week_start,
        "prediction_source": prediction_source,
        "has_monthly_data": has_monthly_data,
        "has_weekly_data": has_weekly_data,
    }
    return render(request, "predictions/sales_prediction.html", context)


@admin_required
def stock_prediction_page(request):
    """
    Renders the latest StockPrediction rows for the upcoming week.
    Falls back to inline computation if no cached predictions exist.
    """
    next_week_start = _get_next_week_start()

    stock_predictions = list(
        StockPrediction.objects
        .filter(week_start=next_week_start)
        .select_related("product")
        .order_by("product__name")
    )
    prediction_source = "cached"

    if not stock_predictions:
        # Inline fallback: generate and cache
        stock_data = forecast_stock_needs()
        prediction_source = "live"
        saved = []
        from catalog.models import Product
        for item in stock_data:
            try:
                product = Product.objects.get(id=item["product_id"])
            except Product.DoesNotExist:
                continue
            sp, _ = StockPrediction.objects.update_or_create(
                product=product,
                week_start=next_week_start,
                defaults={"predicted_qty": item["predicted_qty"]},
            )
            saved.append(sp)
        stock_predictions = saved

    context = {
        "stock_predictions": stock_predictions,
        "next_week_start": next_week_start,
        "prediction_source": prediction_source,
    }
    return render(request, "predictions/stock_prediction.html", context)
