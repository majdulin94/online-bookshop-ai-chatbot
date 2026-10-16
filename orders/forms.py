from django import forms
from .models import ReturnRequest, ReturnRequestItem
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import User

class PlaceOrderForm(forms.Form):
    """
    Form to create an order, including shipping address.
    (Books are selected from the cart, not entered manually!)
    """
    address_line1 = forms.CharField(label="Street and Number", max_length=255, required=True)
    address_line2 = forms.CharField(label="Additional info", max_length=255, required=False)
    city = forms.CharField(max_length=100, required=True)
    postal_code = forms.CharField(max_length=20, required=True)
    country = forms.CharField(max_length=50, required=True)
    phone = forms.CharField(max_length=20, required=False)

class ReturnRequestForm(forms.ModelForm):
    """Form for the ReturnRequest itself (does not need any fields)"""
    class Meta:
        model = ReturnRequest
        fields = []

class ReturnRequestItemForm(forms.ModelForm):
    """
    Form for a single return item.
    - Allows specifying the quantity to return for a specific book.
    - Uses allowed_books to restrict selection.
    - Uses max_quantities for per-book validation.
    """
    class Meta:
        model = ReturnRequestItem
        fields = ['book', 'quantity']

    def __init__(self, *args, **kwargs):
        allowed_books = kwargs.pop('allowed_books', None)
        self.max_quantities = kwargs.pop('max_quantities', {})  # Store max quantities per book
        super().__init__(*args, **kwargs)

        # Restrict available books
        if allowed_books is not None:
            self.fields['book'].queryset = allowed_books

        # Set min/max for the quantity widget and help text
        if 'book' in self.initial:
            book_id = self.initial['book']
            max_qty = self.max_quantities.get(int(book_id), 1)
            self.fields['quantity'].widget.attrs['max'] = max_qty
            self.fields['quantity'].widget.attrs['min'] = 0
            self.fields['quantity'].help_text = f"Max: {max_qty}"

    def clean_quantity(self):
        qty = self.cleaned_data.get('quantity')
        book = self.cleaned_data.get('book')
        # Use self.max_quantities instead of initial (important!)
        max_qty = self.max_quantities.get(book.id if book else None, 1)
        if qty > max_qty:
            raise forms.ValidationError(f"Return quantity cannot exceed ordered quantity ({max_qty}).")
        return qty

class GuestCheckoutForm(forms.Form):
    """
    Form for guest checkout: collects email, password, and shipping info.
    """
    email = forms.EmailField(label="E-Mail", required=True)
    password = forms.CharField(
        widget=forms.PasswordInput,
        min_length=6,
        required=True,
        label="Password"
    )
    address_line1 = forms.CharField(label="Street and Number", max_length=255, required=True)
    address_line2 = forms.CharField(label="Additional info", max_length=255, required=False)
    city = forms.CharField(max_length=100, required=True)
    postal_code = forms.CharField(max_length=20, required=True)
    country = forms.CharField(max_length=50, required=True)
    phone = forms.CharField(max_length=20, required=False)

    def clean(self):
        data = super().clean()
        email = data.get("email")
        if email and (User.objects.filter(username=email).exists() or User.objects.filter(email__iexact=email).exists()):
            self.add_error("email", "An account with this email already exists. Please log in.")
        if data.get("password"):
            validate_password(data["password"], User(username=email or "", email=email or ""))
        return data
