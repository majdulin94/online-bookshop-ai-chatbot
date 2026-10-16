from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from myshop.books.models import Book

class Order(models.Model):
    """
    Order model.
    - user: The User who placed the order
    - total_price: The total price of the order
    - status: pending/shipped/delivered/returned/...
    - created_at: The date the order was created
    - address/city/postal_code/country/phone: shipping info
    - updated_at: track last update
    """
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PAID", "Paid"),
        ("SHIPPED", "Shipped"),
        ("DELIVERED", "Delivered"),
        ("RETURN_REQUESTED", "Return Requested"),
        ("RETURNED", "Returned"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    total_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    stripe_session_id = models.CharField(max_length=255, blank=True, default="", db_index=True)

    @property
    def shipping(self):
        return Decimal("3.95") if self.total_price < Decimal("30") else Decimal("0")

    @property
    def tax(self):
        return ((self.total_price + self.shipping) * Decimal("0.19")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def payable_total(self):
        return self.total_price + self.shipping + self.tax
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING"
    )
    # Shipping address fields
    address_line1 = models.CharField("Street and Number", max_length=255)
    address_line2 = models.CharField("Additional info", max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=50)
    phone = models.CharField(max_length=20, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Automatically updates on every save

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=8, decimal_places=2)

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.total_price = self.book.price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.book.title} × {self.quantity}"

class ReturnRequest(models.Model):
    REQUEST_STATUS = [
        ("REQUESTED", "Requested"),
        ("PROCESSED", "Processed"),
    ]
    order = models.ForeignKey(
        Order,
        related_name="return_requests",
        on_delete=models.CASCADE
    )
    refund_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20,
        choices=REQUEST_STATUS,
        default="REQUESTED"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    # many-to-many relationship with Book through ReturnRequestItem
    books = models.ManyToManyField(
        Book,
        through="ReturnRequestItem",
        related_name="return_requests"
    )

    def __str__(self):
        return f"Return #{self.id} for Order #{self.order.id}"


class ReturnRequestItem(models.Model):
    """
    Represents an item (book) being returned as part of a return request,
    along with the quantity being returned.
    """
    return_request = models.ForeignKey(ReturnRequest, on_delete=models.CASCADE, related_name="items")
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.book.title} x {self.quantity} (ReturnReq #{self.return_request.id})"
