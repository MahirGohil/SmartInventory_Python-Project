from django.urls import path
from cart import views

app_name = "cart"

urlpatterns = [
    path("", views.view_cart, name="view"),
    path("add/", views.add_item, name="add"),
    path("update/", views.update_quantity, name="update"),
    path("remove/", views.remove_item, name="remove"),
    path("discard/", views.discard_cart, name="discard"),
    path("buy/", views.buy_confirm, name="buy_confirm"),
]
