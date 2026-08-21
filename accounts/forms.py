import re
from django import forms
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from accounts.models import User

mobile_validator = RegexValidator(
    regex=r'^\d{10}$',
    message="Mobile number must be exactly 10 digits."
)

def validate_password_strength(value):
    if len(value) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    if not re.search(r'\d', value):
        raise ValidationError("Password must contain at least one digit.")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-\+\=\[\]\\\/]', value):
        raise ValidationError("Password must contain at least one special character.")

class RegistrationForm(forms.Form):
    email = forms.EmailField(required=True)
    mobile_number = forms.CharField(max_length=10, validators=[mobile_validator], required=True)
    username = forms.CharField(max_length=150, required=True)
    password = forms.CharField(widget=forms.PasswordInput, validators=[validate_password_strength], required=True)

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise ValidationError("Username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email address is already registered.")
        return email

    def clean_mobile_number(self):
        mobile_number = self.cleaned_data.get("mobile_number")
        if User.objects.filter(mobile_number=mobile_number).exists():
            raise ValidationError("Mobile number is already registered.")
        return mobile_number


class LoginForm(forms.Form):
    username = forms.CharField(max_length=150, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)


class ForgotPasswordForm(forms.Form):
    username = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        email = cleaned_data.get("email")

        if username and email:
            user = User.objects.filter(username=username, email=email).first()
            if not user:
                raise ValidationError("Username and Email ID do not match any existing user.")
            cleaned_data["user"] = user
        return cleaned_data


class OTPForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        required=True,
        validators=[RegexValidator(regex=r'^\d{6}$', message="OTP must be exactly 6 digits.")]
    )


class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput,
        validators=[validate_password_strength],
        required=True,
        label="New Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        required=True,
        label="Confirm Password"
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password and new_password != confirm_password:
            raise ValidationError("New Password and Confirm Password do not match.")
        return cleaned_data


class ProfilePictureForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["profile_picture"]

