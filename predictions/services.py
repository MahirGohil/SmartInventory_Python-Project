"""
predictions/services.py — Aggregation queries and forecasting logic.

All SQL-level aggregation follows the exact query patterns specified in
smart_inventory_database_structure.md §3.1 and §3.2.

Forecast algorithm: WEIGHTED MOVING AVERAGE (WMA) over the last 4-8 weeks.
  - Weights are linearly increasing (most recent week gets highest weight).
  - This can later be swapped for Holt-Winters (statsmodels) or Facebook
    Prophet once enough historical data (≥ 12 months) has accumulated, per
    spec §9.1. The swap only requires replacing the body of
    forecast_next_week_sales() and forecast_stock_needs() — all callers and
    data models remain unchanged.
"""

from decimal import Decimal
from datetime import date, timedelta

from django.db.models import Sum, F
from django.db.models.functions import TruncMonth, TruncWeek
from django.utils import timezone

from orders.models import Orders, OrderItem
from catalog.models import Product


# ─────────────────────────────────────────────────────────────────────────────
# §3.1 — Monthly Sales Aggregation
# ─────────────────────────────────────────────────────────────────────────────

def get_monthly_sales(year: int) -> list[dict]:
    """
    Returns total sales amount grouped by calendar month for a given year.

    Implements the monthly_sales query from database structure §3.1:
        SELECT TruncMonth(placed_at), SUM(total_amount)
        FROM orders
        WHERE status='completed' AND year=<year>
        GROUP BY month

    Returns a list of 12 dicts (one per month, zero-filled if no data):
        [{"month": 1, "label": "Jan", "total": Decimal}, ...]
    """
    MONTH_LABELS = [
        "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]

    qs = (
        Orders.objects
        .filter(status="completed", placed_at__year=year)
        .annotate(month=TruncMonth("placed_at"))
        .values("month")
        .annotate(total=Sum("total_amount"))
        .order_by("month")
    )

    # Build lookup keyed by month number
    totals_by_month = {row["month"].month: row["total"] for row in qs}

    result = []
    for m in range(1, 13):
        result.append({
            "month": m,
            "label": MONTH_LABELS[m],
            "total": float(totals_by_month.get(m, Decimal("0.00"))),
        })
    return result


# ─────────────────────────────────────────────────────────────────────────────
# §3.1 — Weekly Sales Aggregation
# ─────────────────────────────────────────────────────────────────────────────

def get_weekly_sales(year: int, month: int) -> list[dict]:
    """
    Returns total sales amount grouped by ISO week for a given year+month.

    Implements the weekly_sales query from database structure §3.1:
        SELECT TruncWeek(placed_at), SUM(total_amount)
        FROM orders
        WHERE status='completed' AND year=<year> AND month=<month>
        GROUP BY week

    Returns a list of dicts:
        [{"week_start": date, "label": "Week 1", "total": float}, ...]
    """
    qs = (
        Orders.objects
        .filter(status="completed", placed_at__year=year, placed_at__month=month)
        .annotate(week_start=TruncWeek("placed_at"))
        .values("week_start")
        .annotate(total=Sum("total_amount"))
        .order_by("week_start")
    )

    result = []
    for i, row in enumerate(qs, start=1):
        result.append({
            "week_start": row["week_start"].date() if hasattr(row["week_start"], "date") else row["week_start"],
            "label": f"Week {i}",
            "total": float(row["total"]),
        })
    return result


# ─────────────────────────────────────────────────────────────────────────────
# §3.2 — Weekly Demand by Product Aggregation
# ─────────────────────────────────────────────────────────────────────────────

def get_weekly_demand_by_product(weeks_back: int = 8) -> dict[int, list[dict]]:
    """
    Returns per-product weekly total quantity sold over the last `weeks_back` weeks.

    Implements the demand_by_product query from database structure §3.2:
        SELECT product_id, TruncWeek(order__placed_at), SUM(quantity)
        FROM order_items
        WHERE order__status='completed' AND placed_at >= cutoff
        GROUP BY product_id, week

    Returns a dict keyed by product_id:
        {
            product_id: [
                {"week_start": date, "total_qty": int},
                ...
            ]
        }
    """
    cutoff = timezone.now() - timedelta(weeks=weeks_back)

    qs = (
        OrderItem.objects
        .filter(order__status="completed", order__placed_at__gte=cutoff)
        .annotate(week_start=TruncWeek("order__placed_at"))
        .values("product_id", "week_start")
        .annotate(total_qty=Sum("quantity"))
        .order_by("product_id", "week_start")
    )

    demand: dict[int, list[dict]] = {}
    for row in qs:
        pid = row["product_id"]
        ws = row["week_start"]
        week_date = ws.date() if hasattr(ws, "date") else ws
        demand.setdefault(pid, []).append({
            "week_start": week_date,
            "total_qty": row["total_qty"],
        })
    return demand


# ─────────────────────────────────────────────────────────────────────────────
# Forecasting — Weighted Moving Average
# ─────────────────────────────────────────────────────────────────────────────

def _weighted_moving_average(series: list[float], window: int = 6) -> float:
    """
    Computes a Weighted Moving Average (WMA) over the last `window` data points.
    Most recent value gets the highest weight (linear weights).

    SWAP POINT: Replace this function body with Holt-Winters (statsmodels) or
    Facebook Prophet once ≥ 12 months of data has accumulated (spec §9.1).
    All callers and the data models remain unchanged.
    """
    if not series:
        return 0.0

    recent = series[-window:]  # take last `window` points
    n = len(recent)
    weights = list(range(1, n + 1))  # [1, 2, ..., n] — most recent gets weight n
    weighted_sum = sum(w * v for w, v in zip(weights, recent))
    return weighted_sum / sum(weights)


def forecast_next_week_sales(weekly_sales_series: list[dict]) -> float:
    """
    Forecasts total sales (in INR) for the upcoming week using WMA.

    `weekly_sales_series` is the output of get_weekly_sales() —
    a list of {"week_start", "label", "total"} dicts ordered by week.

    Returns a float representing the predicted sales total for next week.
    Returns 0.0 if there is insufficient data (< 2 weeks).

    SWAP POINT (spec §9.1): Replace _weighted_moving_average() call below with
    a call to statsmodels.tsa.holtwinters.ExponentialSmoothing or Prophet
    for a stronger forecast once more historical data exists.
    """
    if len(weekly_sales_series) < 2:
        return 0.0

    totals = [row["total"] for row in weekly_sales_series]
    return round(_weighted_moving_average(totals, window=min(6, len(totals))), 2)


def forecast_stock_needs() -> list[dict]:
    """
    For each product with recent order history, forecasts the quantity
    needed in the upcoming week using WMA over its weekly demand series.

    Returns a list of dicts:
        [{"product_id": int, "product_name": str, "predicted_qty": int}, ...]

    Products with no order history in the last 8 weeks are omitted —
    they have no meaningful signal to forecast from.

    SWAP POINT (spec §9.1): See _weighted_moving_average() for the model swap note.
    """
    demand_map = get_weekly_demand_by_product(weeks_back=8)
    product_ids = list(demand_map.keys())
    products = Product.objects.filter(id__in=product_ids).only("id", "name")
    name_map = {p.id: p.name for p in products}

    results = []
    for product_id, weekly_series in demand_map.items():
        qty_series = [row["total_qty"] for row in weekly_series]
        predicted = _weighted_moving_average(qty_series, window=min(6, len(qty_series)))
        predicted_qty = max(1, round(predicted))  # floor at 1 — never predict 0 for active products

        results.append({
            "product_id": product_id,
            "product_name": name_map.get(product_id, f"Product #{product_id}"),
            "predicted_qty": predicted_qty,
        })

    results.sort(key=lambda x: x["product_name"])
    return results
