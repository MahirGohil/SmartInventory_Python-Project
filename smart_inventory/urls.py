"""
URL configuration for smart_inventory project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('', include('catalog.urls')),
    path('cart/', include('cart.urls')),
    path('orders/', include('orders.urls')),
    path('adminpanel/', include('adminpanel.urls')),
    path('predictions/', include('predictions.urls')),

    # Serve media files unconditionally (works regardless of DEBUG setting).
    # Django's static() helper is intentionally a no-op when DEBUG=False, which
    # caused all /media/... URLs (product images, profile pictures, bill PDFs) to
    # return 404.  Using serve() directly here fixes that for the dev-server
    # deployment model this project uses.  In a true cloud deployment (Render /
    # Railway / S3) this route is superseded by the platform's file-serving layer.
    re_path(
        r'^media/(?P<path>.*)$',
        serve,
        {'document_root': settings.MEDIA_ROOT},
    ),
]
