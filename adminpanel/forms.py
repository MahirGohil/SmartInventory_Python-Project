from django import forms
from catalog.models import Product, Category


class ProductAddForm(forms.ModelForm):
    """Full product creation form for admin use."""

    class Meta:
        model = Product
        fields = ["name", "product_code", "category", "price", "stock_qty", "photo", "expiry_date"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Product name"}),
            "product_code": forms.TextInput(attrs={"class": "form-control", "placeholder": "Unique product code"}),
            "category": forms.Select(attrs={"class": "form-control"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "placeholder": "Price in INR"}),
            "stock_qty": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "expiry_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["expiry_date"].required = False
        self.fields["photo"].required = False


class ProductEditForm(forms.ModelForm):
    """
    Restricted product edit form per spec §8.4.
    Editable fields: Name, Product Code (product_code), Quantity, Category.

    NOTE (spec §8.4 oversight): Price and Photo are intentionally excluded per the
    spec. If admins should also be able to update price or swap photos, add
    "price" and "photo" to the `fields` list below — no other changes needed.
    """

    class Meta:
        model = Product
        fields = ["name", "product_code", "stock_qty", "category"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Product name"}),
            "product_code": forms.TextInput(attrs={"class": "form-control"}),
            "stock_qty": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "category": forms.Select(attrs={"class": "form-control"}),
        }
