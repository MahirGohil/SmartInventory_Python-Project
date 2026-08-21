from django.urls import path
from adminpanel import views

app_name = "adminpanel"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("products/", views.manage_products, name="manage_products"),
    path("products/add/", views.add_product, name="add_product"),
    path("products/<int:product_id>/edit/", views.edit_product, name="edit_product"),
    path("products/<int:product_id>/delete/", views.delete_product, name="delete_product"),
    path("notifications/", views.notifications_list, name="notifications"),
    path("notifications/<int:notification_id>/read/", views.mark_notification_read, name="mark_notification_read"),
]
