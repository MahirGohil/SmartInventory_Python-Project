from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    mobile_number = models.CharField(max_length=10, unique=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)
    joining_date = models.DateField(auto_now_add=True)
    has_used_first_order_discount = models.BooleanField(default=False)

class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["user", "is_used"])]

