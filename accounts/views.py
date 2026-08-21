from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from django.urls import NoReverseMatch

from accounts.models import User, OTP
from orders.models import Orders
from accounts.forms import (
    RegistrationForm,
    LoginForm,
    ForgotPasswordForm,
    OTPForm,
    ResetPasswordForm,
    ProfilePictureForm,
)
from accounts.utils import generate_otp, resend_otp, OTPEmailSendError


def landing(request):
    """Landing page with full-screen shop background and Login/Sign Up options."""
    # BUG 6 FIX: Redirect already-authenticated users directly to the shop,
    # consistent with the same guard in login_view() and register().
    if request.user.is_authenticated:
        return _redirect_to_shop()
    return render(request, "accounts/landing.html")


def register(request):
    """User registration view."""
    if request.user.is_authenticated:
        return _redirect_to_shop()

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                mobile_number=form.cleaned_data["mobile_number"],
                password=form.cleaned_data["password"],
            )
            login(request, user)
            messages.success(request, "Registration successful! Welcome to Smart Inventory.")
            return _redirect_to_shop()
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    """User login view."""
    if request.user.is_authenticated:
        return _redirect_to_shop()

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                return _redirect_to_shop()
            else:
                messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    """Logs out the user and redirects to landing page."""
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("accounts:landing")


def forgot_password(request):
    """Forgot Password view validating username + email and sending OTP."""
    if request.method == "POST":
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data["user"]
            try:
                generate_otp(user)
            except OTPEmailSendError as exc:
                # This page suppresses the global messages toast (see template)
                # and renders errors via form.non_field_errors instead, so the
                # failure must be attached to the form, not messages.error().
                form.add_error(None, str(exc))
                return render(request, "accounts/forgot_password.html", {"form": form})
            request.session["reset_user_id"] = user.id
            messages.success(request, f"An OTP has been sent to {user.email}.")
            return redirect("accounts:verify_otp")
    else:
        form = ForgotPasswordForm()

    return render(request, "accounts/forgot_password.html", {"form": form})


def verify_otp(request):
    """OTP verification view with expiration check and resend functionality."""
    user_id = request.session.get("reset_user_id")
    if not user_id:
        messages.error(request, "Please enter your username and email first.")
        return redirect("accounts:forgot_password")

    user = User.objects.filter(id=user_id).first()
    if not user:
        return redirect("accounts:forgot_password")

    # Handle explicit resend OTP request
    if request.method == "POST" and request.POST.get("action") == "resend":
        try:
            resend_otp(user)
        except OTPEmailSendError as exc:
            messages.error(request, str(exc))
            return redirect("accounts:verify_otp")
        messages.success(request, "A new 6-digit OTP has been sent to your email.")
        return redirect("accounts:verify_otp")

    if request.method == "POST":
        form = OTPForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"]
            latest_otp = (
                OTP.objects.filter(user=user, is_used=False)
                .order_by("-created_at")
                .first()
            )

            if not latest_otp:
                form.add_error("code", "No active OTP found. Please click Resend OTP.")
            elif latest_otp.expires_at < timezone.now():
                form.add_error("code", "OTP has expired. Please click Resend OTP.")
            elif latest_otp.code != code:
                form.add_error("code", "Incorrect OTP code. Please try again.")
            else:
                # OTP is valid
                request.session["otp_verified_user_id"] = user.id
                return redirect("accounts:reset_password")
    else:
        form = OTPForm()

    return render(request, "accounts/otp_verify.html", {"form": form, "user_email": user.email})


def reset_password(request):
    """Reset Password view updating password using set_password()."""
    verified_user_id = request.session.get("otp_verified_user_id")
    if not verified_user_id:
        messages.error(request, "Unauthorized access to password reset.")
        return redirect("accounts:forgot_password")

    user = User.objects.filter(id=verified_user_id).first()
    if not user:
        return redirect("accounts:forgot_password")

    if request.method == "POST":
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data["new_password"]
            user.set_password(new_password)
            user.save()

            # Mark active OTPs as used
            OTP.objects.filter(user=user, is_used=False).update(is_used=True)

            # Clear session keys
            request.session.pop("reset_user_id", None)
            request.session.pop("otp_verified_user_id", None)

            messages.success(request, "Password updated successfully! Please log in.")
            return redirect("accounts:login")
    else:
        form = ResetPasswordForm()

    return render(request, "accounts/reset_password.html", {"form": form})


@login_required(login_url="accounts:login")
def profile(request):
    """User profile view with profile picture upload form and real order history."""
    order_history = (
        Orders.objects.filter(user=request.user)
        .prefetch_related("items")
        .order_by("-placed_at")[:5]
    )

    picture_form = ProfilePictureForm(instance=request.user)
    return render(request, "accounts/profile.html", {
        "user": request.user,
        "picture_form": picture_form,
        "order_history": order_history,
    })


@login_required(login_url="accounts:login")
@require_POST
def update_profile_picture(request):
    """POST-only view to handle user profile picture uploads."""
    form = ProfilePictureForm(request.POST, request.FILES, instance=request.user)
    if form.is_valid():
        form.save()
        messages.success(request, "Profile picture updated successfully!")
    else:
        messages.error(request, "Failed to update profile picture. Please upload a valid image.")
    return redirect("accounts:profile")


def _redirect_to_shop():
    """Redirects to catalog:shop."""
    return redirect("catalog:shop")
