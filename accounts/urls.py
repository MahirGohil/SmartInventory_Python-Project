from django.urls import path
from accounts import views

app_name = "accounts"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path("reset-password/", views.reset_password, name="reset_password"),
    path("profile/", views.profile, name="profile"),
    path("profile/upload-picture/", views.update_profile_picture, name="update_profile_picture"),
]
