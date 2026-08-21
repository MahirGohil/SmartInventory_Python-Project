import logging
import random
import smtplib
import socket
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from accounts.models import OTP

logger = logging.getLogger(__name__)


class OTPEmailSendError(Exception):
    """Raised when the OTP email could not be delivered (SMTP/network failure)."""
    pass


def generate_otp(user):
    """
    Invalidates any previous unused OTP for the user, creates a new random
    6-digit OTP valid for 1 minute, and emails it using Django's mail system.
    """
    # Invalidate previous unused OTPs for this user
    OTP.objects.filter(user=user, is_used=False).update(is_used=True)

    # Generate 6-digit code
    code = f"{random.randint(0, 999999):06d}"
    expires_at = timezone.now() + timedelta(minutes=1)

    otp = OTP.objects.create(
        user=user,
        code=code,
        expires_at=expires_at,
        is_used=False
    )

    # Email the code
    subject = "Smart Inventory - Password Reset OTP"
    message = (
        f"Hello {user.username},\n\n"
        f"Your OTP for resetting your password is: {code}\n"
        f"This code will expire in 1 minute.\n\n"
        f"If you did not request this, please ignore this email.\n\n"
        f"Smart Inventory Team"
    )
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@smartinventory.com"),
            recipient_list=[user.email],
            fail_silently=False,
        )
    except (smtplib.SMTPException, socket.timeout, OSError) as exc:
        # Don't leave a "used" OTP with no email ever sent — mark it used so
        # a stale/undelivered code can't be guessed or reused, then surface
        # a clean error the view can show to the user instead of a 500 page.
        otp.is_used = True
        otp.save(update_fields=["is_used"])
        logger.exception("Failed to send OTP email to %s", user.email)
        raise OTPEmailSendError(
            "Could not send the OTP email. Please try again in a moment."
        ) from exc

    return otp


def resend_otp(user):
    """
    Invalidates any existing unused OTP for the user, generates a new 6-digit
    OTP valid for 1 minute, and emails it.  Delegates entirely to generate_otp()
    which already handles the invalidation step — no need to duplicate it here.
    """
    # BUG 8 FIX: Removed redundant OTP.objects.filter(...).update(is_used=True)
    # that was here before.  generate_otp() already does this as its first action
    # (see line 14 above), so calling it twice caused unnecessary DB writes and
    # would have incorrectly invalidated the brand-new OTP if resend was triggered
    # in rapid succession.
    return generate_otp(user)
