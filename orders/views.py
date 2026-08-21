from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.utils import timezone

from orders.models import Orders, Bill
from cart.services import get_or_create_cart, calculate_totals, get_or_generate_delivery_eta
from orders.forms import CheckoutForm
from orders.services import create_order, generate_bill


@login_required(login_url="accounts:login")
def checkout_page(request):
    """
    GET /orders/checkout/
    Renders Checkout form with pre-filled user mobile number and session delivery ETA.
    """
    cart = get_or_create_cart(request.user)
    items = cart.items.select_related("product").all()

    if not items.exists():
        messages.warning(request, "Your cart is empty. Please add items before checking out.")
        return redirect("catalog:shop")

    totals = calculate_totals(cart)
    delivery_eta = get_or_generate_delivery_eta(request)

    # Initial form data pre-filling receiver name/mobile from profile defaults
    initial_data = {
        "receiver_name": request.user.username,
        "receiver_mobile": request.user.mobile_number,
        "payment_method": "UPI",
    }
    form = CheckoutForm(initial=initial_data)

    context = {
        "form": form,
        "cart_items": items,
        "totals": totals,
        "delivery_eta": delivery_eta,
        "user_mobile": request.user.mobile_number,
    }
    return render(request, "orders/checkout.html", context)


@login_required(login_url="accounts:login")
@require_POST
def place_order(request):
    """
    POST /orders/place-order/
    Processes checkout form, validates cart server-side, creates order & bill,
    and renders order confirmation.
    """
    cart = get_or_create_cart(request.user)
    if not cart.items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("catalog:shop")

    form = CheckoutForm(request.POST)
    if not form.is_valid():
        totals = calculate_totals(cart)
        delivery_eta = get_or_generate_delivery_eta(request)
        return render(request, "orders/checkout.html", {
            "form": form,
            "cart_items": cart.items.select_related("product").all(),
            "totals": totals,
            "delivery_eta": delivery_eta,
            "user_mobile": request.user.mobile_number,
        })

    # Retrieve session delivery ETA
    eta_str = request.session.get("delivery_eta")
    delivery_eta_dt = None
    if eta_str:
        try:
            delivery_eta_dt = timezone.datetime.fromisoformat(eta_str)
        except (ValueError, TypeError):
            pass

    # Create Order & OrderItems
    order = create_order(
        user=request.user,
        cart=cart,
        checkout_data=form.cleaned_data,
        delivery_eta_dt=delivery_eta_dt
    )

    # Generate PDF Bill
    bill = generate_bill(order)

    # Clear session delivery_eta after successful placement
    request.session.pop("delivery_eta", None)

    # Branch on payment_method for confirmation message per spec §5.2
    payment_method = form.cleaned_data.get("payment_method")
    if payment_method == "COD":
        # COD message per spec §5.2
        confirmation_message = "Thank you for Placing Order. Your Order will be delivered Shortly."
        auto_download = False
    else:
        # UPI Payment Gateway Placeholder — simulated successful payment per spec §5.2
        # TODO: Replace simulated payment response below with real UPI Payment Gateway SDK (e.g. Razorpay/UPI intent)
        confirmation_message = "Thank you for Purchasing."
        auto_download = True

    context = {
        "order": order,
        "bill": bill,
        "confirmation_message": confirmation_message,
        "auto_download": auto_download,
        "payment_method": payment_method,
    }
    return render(request, "orders/order_confirmation.html", context)


@login_required(login_url="accounts:login")
def order_history(request):
    """
    GET /orders/history/
    Lists user's past orders with links to view and re-download bills.
    """
    orders = Orders.objects.filter(user=request.user).order_by("-placed_at").prefetch_related("items", "bill")
    return render(request, "orders/order_history.html", {"orders": orders})


@login_required(login_url="accounts:login")
def download_bill(request, order_id):
    """
    GET /orders/bill/<order_id>/
    Serves the PDF bill for an order with ownership security check.
    """
    order = get_object_or_404(Orders, id=order_id)

    # Ownership check: user can only access their own bills unless staff
    if order.user != request.user and not request.user.is_staff:
        return HttpResponseForbidden("You are not authorized to access this bill.")

    try:
        bill = order.bill
        if not bill.pdf_file:
            bill = generate_bill(order)
    except Bill.DoesNotExist:
        # BUG 7 FIX: 'Orders.bill.RelatedObjectDoesNotExist' is not a valid
        # exception reference — Bill.DoesNotExist is the correct class raised
        # when a OneToOneField reverse relation has no related object.
        bill = generate_bill(order)

    filename = f"SmartInventory_Bill_Order_{order.id}.pdf"
    return FileResponse(
        bill.pdf_file.open("rb"),
        as_attachment=True,
        filename=filename,
        content_type="application/pdf"
    )
