from django import forms
from django.core.validators import RegexValidator

mobile_validator = RegexValidator(
    regex=r'^\d{10}$',
    message="Mobile number must be exactly 10 digits."
)

class CheckoutForm(forms.Form):
    PAYMENT_CHOICES = [
        ("UPI", "UPI Payment"),
        ("COD", "Cash on Delivery (COD)"),
    ]

    receiver_name = forms.CharField(
        max_length=100,
        required=True,
        label="Receiver Name",
        widget=forms.TextInput(attrs={
            "placeholder": "Full name of recipient",
            "class": "form-control",
        })
    )

    # TODO (spec §5.1): Integrate Google Places Autocomplete API.
    # Currently stubbed as a plain text input so checkout flow is testable end-to-end without external API keys.
    formatted_address = forms.CharField(
        max_length=255,
        required=True,
        label="Delivery Address",
        widget=forms.TextInput(attrs={
            "placeholder": "Enter delivery address (Google Places Autocomplete target)",
            "class": "form-control",
            "id": "id_formatted_address",
        })
    )

    receiver_mobile = forms.CharField(
        max_length=10,
        validators=[mobile_validator],
        required=True,
        label="Receiver Mobile Number",
        widget=forms.TextInput(attrs={
            "placeholder": "10-digit mobile number",
            "class": "form-control",
            "maxlength": "10",
        })
    )

    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "payment-radio"}),
        initial="UPI",
        required=True,
        label="Payment Method"
    )
