from django import forms
from books.models import book  # or Book if you've renamed it

class CartUpdateForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        max_value=99,
        widget=forms.NumberInput(attrs={
            "class": "form-control quantity-input",
            "min": 1,
            "max": 99
        })
    )
    product_id = forms.IntegerField(widget=forms.HiddenInput())

    # Optional: Add validation or clean methods if needed
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is None:
            raise forms.ValidationError("Please specify a quantity.")
        return quantity
