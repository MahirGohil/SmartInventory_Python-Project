import json
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import NoReverseMatch

from cart.models import Cart, CartItem
from catalog.models import Product
from cart.services import (
    get_or_create_cart,
    calculate_totals,
    get_or_generate_delivery_eta,
)


def _parse_json_body(request):
    """Helper to parse JSON payload from request body."""
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return {}


@login_required(login_url="accounts:login")
@require_POST
def add_item(request):
    """
    POST /cart/add/
    Payload: {"product_id": int, "quantity": int}
    """
    data = _parse_json_body(request)
    product_id = data.get("product_id")
    quantity = int(data.get("quantity", 1))

    if not product_id:
        return JsonResponse({"success": False, "error": "Missing product_id"}, status=400)

    product = get_object_or_404(Product, id=product_id)
    cart = get_or_create_cart(request.user)

    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        cart_item.quantity += quantity
    else:
        cart_item.quantity = quantity
    cart_item.save()

    totals = calculate_totals(cart)
    return JsonResponse({
        "success": True,
        "quantity": cart_item.quantity,
        "cart_total_items": totals["item_count"],
        "cart_total_amount": float(totals["total_amount"]),
    })


@login_required(login_url="accounts:login")
@require_POST
def update_quantity(request):
    """
    POST /cart/update/
    Payload: {"product_id": int, "quantity": int}
    """
    data = _parse_json_body(request)
    product_id = data.get("product_id")

    if not product_id or "quantity" not in data:
        return JsonResponse({"success": False, "error": "Missing product_id or quantity"}, status=400)

    quantity = int(data.get("quantity", 0))
    cart = get_or_create_cart(request.user)
    cart_item = CartItem.objects.filter(cart=cart, product_id=product_id).first()

    if not cart_item:
        return JsonResponse({"success": False, "error": "Item not in cart"}, status=404)

    if quantity <= 0:
        cart_item.delete()
        new_quantity = 0
        removed = True
    else:
        cart_item.quantity = quantity
        cart_item.save()
        new_quantity = cart_item.quantity
        removed = False

    totals = calculate_totals(cart)
    return JsonResponse({
        "success": True,
        "quantity": new_quantity,
        "removed": removed,
        "cart_total_items": totals["item_count"],
        "cart_total_amount": float(totals["total_amount"]),
    })


@login_required(login_url="accounts:login")
@require_POST
def remove_item(request):
    """
    POST /cart/remove/
    Payload: {"product_id": int}
    """
    data = _parse_json_body(request)
    product_id = data.get("product_id")

    if not product_id:
        return JsonResponse({"success": False, "error": "Missing product_id"}, status=400)

    cart = get_or_create_cart(request.user)
    CartItem.objects.filter(cart=cart, product_id=product_id).delete()

    totals = calculate_totals(cart)
    return JsonResponse({
        "success": True,
        "quantity": 0,
        "removed": True,
        "cart_total_items": totals["item_count"],
        "cart_total_amount": float(totals["total_amount"]),
    })


@login_required(login_url="accounts:login")
@require_POST
def discard_cart(request):
    """
    POST /cart/discard/
    Deletes all CartItems for the user's cart and clears session delivery_eta.
    """
    cart = get_or_create_cart(request.user)
    cart.items.all().delete()
    request.session.pop("delivery_eta", None)

    return JsonResponse({"success": True, "cart_total_items": 0, "cart_total_amount": 0.0})


@login_required(login_url="accounts:login")
def view_cart(request):
    """
    GET /cart/
    Renders the Cart page with items, quantities, line totals, subtotal, discount,
    delivery charge, final total, and session-persisted delivery ETA.
    """
    cart = get_or_create_cart(request.user)
    items = cart.items.select_related("product").all()

    # Calculate line totals for template display
    cart_items_with_totals = []
    for item in items:
        line_total = item.product.price * item.quantity
        cart_items_with_totals.append({
            "id": item.id,
            "product": item.product,
            "quantity": item.quantity,
            "line_total": line_total,
        })

    totals = calculate_totals(cart)
    delivery_eta = get_or_generate_delivery_eta(request) if items.exists() else None
    delivery_eta_end = delivery_eta + timedelta(minutes=30) if delivery_eta else None

    context = {
        "cart_items": cart_items_with_totals,
        "totals": totals,
        "delivery_eta": delivery_eta,
        "delivery_eta_end": delivery_eta_end,
    }
    return render(request, "cart/cart_page.html", context)


@login_required(login_url="accounts:login")
def buy_confirm(request):
    """Redirects to orders:checkout when confirmed."""
    cart = get_or_create_cart(request.user)
    if not cart.items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("catalog:shop")

    return redirect("orders:checkout")
