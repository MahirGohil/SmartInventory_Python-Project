from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
import functools

from catalog.models import Category, Product
from adminpanel.models import Notification
from adminpanel.forms import ProductAddForm, ProductEditForm
from adminpanel.services import check_product_notifications, sync_all_notifications


def admin_required(view_func):
    """
    Decorator that ensures the user is logged in AND is a superuser.
    Non-admins are redirected to the shop page (standard e-commerce UX per spec).
    """
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


@admin_required
def dashboard(request):
    """
    Admin dashboard landing page (spec §8).
    Shows top-left nav, search bar, profile icon, and summary stats.
    """
    sync_all_notifications()

    total_products = Product.objects.count()
    low_stock_count = Notification.objects.filter(type="low_stock", is_read=False).count()
    expiry_count = Notification.objects.filter(type__in=["expiry_warning", "expired"], is_read=False).count()
    unread_notifications = Notification.objects.filter(is_read=False).count()

    context = {
        "total_products": total_products,
        "low_stock_count": low_stock_count,
        "expiry_count": expiry_count,
        "unread_notifications": unread_notifications,
    }
    return render(request, "adminpanel/dashboard.html", context)


@admin_required
def manage_products(request):
    """
    Lists all products with Name, Product ID, Quantity, Edit, Delete actions (spec §8.4).
    """
    search_query = request.GET.get("q", "").strip()
    products = Product.objects.select_related("category").all()
    if search_query:
        products = products.filter(name__icontains=search_query)
    products = products.order_by("name")

    context = {
        "products": products,
        "search_query": search_query,
    }
    return render(request, "adminpanel/manage_products.html", context)


@admin_required
def add_product(request):
    """
    GET: shows ProductAddForm.
    POST: saves new product, immediately visible on the shop page (same Product table).
    """
    if request.method == "POST":
        form = ProductAddForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            check_product_notifications(product)
            messages.success(request, f"Product '{product.name}' added successfully.")
            return redirect("adminpanel:manage_products")
    else:
        form = ProductAddForm()

    return render(request, "adminpanel/add_product.html", {"form": form})


@admin_required
def edit_product(request, product_id):
    """
    GET: shows ProductEditForm pre-filled with the product.
    POST: saves changes and redirects to manage_products.
    """
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        form = ProductEditForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            check_product_notifications(product)
            messages.success(request, f"Product '{product.name}' updated successfully.")
            return redirect("adminpanel:manage_products")
    else:
        form = ProductEditForm(instance=product)

    return render(request, "adminpanel/edit_product.html", {"form": form, "product": product})


@admin_required
@require_POST
def delete_product(request, product_id):
    """
    POST only. Client-side confirm dialog triggers this; removes the product.
    Returns JSON so adminpanel.js can remove the row from DOM without full reload.
    """
    product = get_object_or_404(Product, id=product_id)
    product_name = product.name
    product.delete()
    return JsonResponse({"success": True, "deleted_name": product_name})


@admin_required
def notifications_list(request):
    """
    Lists Notification rows grouped by type (spec §8.5).
    Supports mark-as-read for individual notifications via AJAX.
    """
    sync_all_notifications()
    filter_type = request.GET.get("filter", "all")

    qs = Notification.objects.select_related("product").all()
    if filter_type != "all":
        qs = qs.filter(type=filter_type)

    notifications = qs.order_by("is_read", "-created_at")

    low_stock = Notification.objects.filter(type="low_stock", is_read=False).count()
    expiry_warning = Notification.objects.filter(type="expiry_warning", is_read=False).count()
    expired = Notification.objects.filter(type="expired", is_read=False).count()

    context = {
        "notifications": notifications,
        "filter_type": filter_type,
        "low_stock_count": low_stock,
        "expiry_warning_count": expiry_warning,
        "expired_count": expired,
    }
    return render(request, "adminpanel/notifications.html", context)


@admin_required
@require_POST
def mark_notification_read(request, notification_id):
    """
    POST. Marks a single notification as read. Returns JSON for AJAX fetch.
    """
    notification = get_object_or_404(Notification, id=notification_id)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return JsonResponse({"success": True, "notification_id": notification_id})
