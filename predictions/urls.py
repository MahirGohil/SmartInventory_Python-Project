from django.urls import path
from predictions import views

app_name = "predictions"

urlpatterns = [
    path("sales/", views.sales_prediction_page, name="sales"),
    path("stock/", views.stock_prediction_page, name="stock"),
]
