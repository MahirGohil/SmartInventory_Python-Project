from django.urls import path
from orders import views

app_name = "orders"

urlpatterns = [
    path("checkout/", views.checkout_page, name="checkout"),
    path("place-order/", views.place_order, name="place_order"),
    path("history/", views.order_history, name="order_history"),
    path("bill/<int:order_id>/", views.download_bill, name="download_bill"),
]
