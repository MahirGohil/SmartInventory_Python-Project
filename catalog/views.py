from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from catalog.models import Category, Product
from orders.models import OrderItem
from cart.models import Cart, CartItem


@login_required(login_url="accounts:login")
def shop(request):
    """
    Main shopping page.

    Query params:
        ?category=<slug>  — filter by category (default: "all")
        ?q=<search term>  — filter by product name (icontains)
    """
    selected_category = request.GET.get("category", "all")
    search_query = request.GET.get("q", "").strip()

    all_categories = Category.objects.all().order_by("name")
    products = Product.objects.select_related("category").all()

    # Category filter
    if selected_category != "all":
        products = products.filter(category__slug=selected_category)

    # Search filter
    if search_query:
        products = products.filter(name__icontains=search_query)

    products = products.order_by("name")

    # --- Previously Bought (spec §2) ---
    # Products the authenticated user has ordered in completed orders, shown
    # as a separate section above the main grid.
    previously_bought = []
    if request.user.is_authenticated:
        bought_ids = (
            OrderItem.objects
            .filter(order__user=request.user, order__status="completed")
            .values_list("product_id", flat=True)
            .distinct()
        )
        if bought_ids.exists():
            previously_bought = Product.objects.filter(id__in=bought_ids)

    # --- Cart state (spec §2 — card render state) ---
    # Keyed by product_id so product_card.html renders the +/- stepper
    # instead of the Add button for items already in the user's cart.
    cart_items = {}
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_items = {
                item.product_id: item.quantity
                for item in CartItem.objects.filter(cart=cart).select_related("product")
            }

    context = {
        "all_categories": all_categories,
        "products": products,
        "selected_category": selected_category,
        "search_query": search_query,
        "previously_bought": previously_bought,
        "cart_items": cart_items,
    }
    return render(request, "catalog/shop.html", context)
