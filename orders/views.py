from decimal import Decimal
from datetime import timedelta
from collections import Counter
import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.forms import modelformset_factory
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_GET, require_http_methods
from myshop.books.models import Book
from myshop.cart.models import CartItem
from myshop.cart.session import get_cart_session
from .models import Order, OrderItem, ReturnRequest, ReturnRequestItem
from .forms import PlaceOrderForm, GuestCheckoutForm, ReturnRequestForm, ReturnRequestItemForm


def valid_cart(items):
    valid = bool(items) and all(
        isinstance(qty, int) and not isinstance(qty, bool) and 1 <= qty <= 999
        and book.price is not None and book.price > 0
        and book.stock_status != "Out of Stock" for book, qty in items
    )
    return valid and sum(book.price * qty for book, qty in items) <= Decimal("999999.99")


def create_pending_order(user, items, address):
    # Called inside an atomic transaction after all input has been validated.
    order = Order.objects.create(user=user, total_price=sum(book.price * qty for book, qty in items),
        **{key: address.get(key) for key in ("address_line1", "address_line2", "city", "postal_code", "country", "phone")})
    for book, qty in items:
        OrderItem.objects.create(order=order, book=book, quantity=qty, total_price=book.price * qty)
    return order


def checkout_page(request, order):
    request.session["pending_order_id"] = order.pk
    return render(request, "orders/stripe_checkout.html", {
        "order": order, "shipping": order.shipping, "tax": order.tax,
        "total": order.payable_total, "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY,
    })


@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def place_order(request):
    items = [(item.book, item.quantity) for item in CartItem.objects.filter(user=request.user).select_related("book")]
    if not items:
        messages.error(request, "Your cart is empty.")
        return redirect("cart:cart_view")
    form = PlaceOrderForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        if valid_cart(items):
            return checkout_page(request, create_pending_order(request.user, items, form.cleaned_data))
        form.add_error(None, "Cart contains unavailable books, invalid quantities, or missing prices.")
    return render(request, "orders/place_order.html", {"form": form, "cart_items": items})


@require_http_methods(["GET", "POST"])
@transaction.atomic
def guest_place_order(request):
    if request.user.is_authenticated:
        return redirect("orders:place_order")
    cart = get_cart_session(request)
    books = Book.objects.in_bulk(list(cart), field_name="slug")
    items = [(books[slug], qty) for slug, qty in cart.items() if slug in books]
    form = GuestCheckoutForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        if len(items) != len(cart) or not valid_cart(items):
            form.add_error(None, "Cart is empty or contains unavailable books, invalid quantities, or missing prices.")
        else:
            email = form.cleaned_data["email"]
            user = User.objects.create_user(username=email, email=email, password=form.cleaned_data["password"])
            order = create_pending_order(user, items, form.cleaned_data)
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return checkout_page(request, order)
    return render(request, "orders/guest_place_order.html", {"guest_form": form, "cart_items": items})


@method_decorator(login_required, name="dispatch")
class OrdersCreateCheckoutSessionView(View):
    def post(self, request, *args, **kwargs):
        if not settings.EXTERNAL_SERVICES_ENABLED:
            return JsonResponse({"error": "Stripe is disabled in isolated validation."}, status=503)
        with transaction.atomic():
            order = get_object_or_404(Order.objects.select_for_update(),
                pk=request.session.get("pending_order_id"), user=request.user, status="PENDING")
            if not order.items.exists() or order.total_price <= 0:
                return JsonResponse({"error": "Invalid order."}, status=400)
            try:
                session = stripe.checkout.Session.create(
                    api_key=settings.STRIPE_SECRET_KEY,
                    idempotency_key="bookshop-order-" + str(order.pk),
                    mode="payment", payment_method_types=["card"],
                    client_reference_id=str(order.pk), metadata={"order_id": str(order.pk)},
                    line_items=[{"price_data": {"currency": "eur",
                        "product_data": {"name": "Bookshop order #" + str(order.pk)},
                        "unit_amount": int(order.payable_total * 100)}, "quantity": 1}],
                    success_url=request.build_absolute_uri(reverse("orders:payment_success")) + "?session_id={CHECKOUT_SESSION_ID}",
                    cancel_url=request.build_absolute_uri(reverse("orders:payment_cancel")),
                    customer_email=order.user.email,
                )
            except stripe.StripeError:
                return JsonResponse({"error": "Payment service unavailable. Please retry."}, status=502)
            order.stripe_session_id = session.id
            order.save(update_fields=["stripe_session_id", "updated_at"])
        return JsonResponse({"id": session.id, "url": session.url})


@login_required
@require_GET
def payment_success(request):
    sid = request.GET.get("session_id", "")
    if not sid or len(sid) > 255:
        return JsonResponse({"error": "Verified checkout session required."}, status=400)
    order = get_object_or_404(Order, stripe_session_id=sid, user=request.user)
    if order.status == "PAID":
        return render(request, "orders/placed.html", {"order": order})
    if order.status != "PENDING":
        return JsonResponse({"error": "Order is not pending."}, status=409)
    if not settings.EXTERNAL_SERVICES_ENABLED:
        return JsonResponse({"error": "Stripe is disabled in isolated validation."}, status=503)
    try:
        checkout = stripe.checkout.Session.retrieve(sid, api_key=settings.STRIPE_SECRET_KEY)
    except stripe.StripeError:
        return JsonResponse({"error": "Unable to verify payment. Please retry."}, status=502)
    if not (checkout.get("id") == sid and checkout.get("payment_status") == "paid"
            and checkout.get("status") == "complete" and checkout.get("mode") == "payment"
            and checkout.get("currency") == "eur"
            and checkout.get("amount_total") == int(order.payable_total * 100)
            and checkout.get("client_reference_id") == str(order.pk)):
        return JsonResponse({"error": "Payment has not been verified."}, status=400)
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        if order.status == "PENDING":
            order.status = "PAID"
            order.save(update_fields=["status", "updated_at"])
            # Remove only purchased quantities, preserving later cart additions.
            guest_cart = get_cart_session(request).copy()
            for item in order.items.select_related("book"):
                cart_item = CartItem.objects.select_for_update().filter(user=request.user, book=item.book).first()
                if cart_item:
                    if cart_item.quantity <= item.quantity:
                        cart_item.delete()
                    else:
                        cart_item.quantity -= item.quantity
                        cart_item.save(update_fields=["quantity"])
                if item.book.slug in guest_cart:
                    remaining = guest_cart[item.book.slug] - item.quantity
                    if remaining > 0:
                        guest_cart[item.book.slug] = remaining
                    else:
                        guest_cart.pop(item.book.slug)
            request.session["cart"] = guest_cart
    if request.session.get("pending_order_id") == order.pk:
        request.session.pop("pending_order_id", None)
    messages.success(request, "Payment verified. Your order has been placed!")
    return render(request, "orders/placed.html", {"order": order})


@require_GET
def payment_cancel(request):
    messages.warning(request, "Payment was cancelled. You can try again.")
    return redirect("orders:place_order")

@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def request_return(request, order_id):
    """
    Allow user to request a return for books from a specific order,
    but only within 14 days of purchase.
    """
    order = get_object_or_404(Order.objects.select_for_update(), id=order_id, user=request.user)
    delta = timezone.now() - order.created_at
    if order.status != "PAID" or delta > timedelta(days=14):
        return render(request, "orders/return_not_allowed.html", {"order": order})

    order_items = order.items.all()
    allowed_books = Book.objects.filter(id__in=order_items.values_list('book_id', flat=True))
    # Map: book_id -> quantity ordered in that order
    returned = ReturnRequestItem.objects.filter(return_request__order=order).values("book_id").annotate(total=Sum("quantity"))
    returned = {row["book_id"]: row["total"] for row in returned}
    max_quantities = {item.book_id: max(0, item.quantity - returned.get(item.book_id, 0)) for item in order_items}

    # Build the formset for all items in this order
    ReturnRequestItemFormSet = modelformset_factory(
        ReturnRequestItem,
        form=ReturnRequestItemForm,
        extra=len(order_items),
        can_delete=False,
    )

    # Initial formset data: one for each order item
    initial_data = [
        {'book': item.book.id, 'quantity': 0}
        for item in order_items
    ]

    if request.method == "POST":
        formset = ReturnRequestItemFormSet(
            request.POST,
            queryset=ReturnRequestItem.objects.none(),
            initial=initial_data,
            # Pass allowed_books and max_quantities to each form in the formset
            form_kwargs={'allowed_books': allowed_books, 'max_quantities': max_quantities}
        )
        req_form = ReturnRequestForm(request.POST)

        if formset.is_valid():
            # Check at least one book is being returned
            has_return = any(form.cleaned_data.get("quantity", 0) > 0 for form in formset)
            requested = Counter()
            for form in formset:
                book = form.cleaned_data.get("book")
                if book:
                    requested[book.pk] += form.cleaned_data.get("quantity", 0)
            exceeds = any(qty > max_quantities.get(book_id, 0) for book_id, qty in requested.items())
            if exceeds:
                messages.error(request, "Total return quantity exceeds the remaining purchased quantity.")
            elif not has_return:
                messages.error(request, "Please specify at least one item to return.")
            else:
                # Create the return request and each return item
                return_request = ReturnRequest.objects.create(
                    order=order,
                    status="REQUESTED",
                )
                for form in formset:
                    book = form.cleaned_data.get("book")
                    qty = form.cleaned_data.get("quantity", 0)
                    if book and qty > 0:
                        ReturnRequestItem.objects.create(
                            return_request=return_request,
                            book=book,
                            quantity=qty,
                        )
                return render(request, "orders/return_requested.html", {"return_request": return_request})
    else:
        formset = ReturnRequestItemFormSet(
            queryset=ReturnRequestItem.objects.none(),
            initial=initial_data,
            form_kwargs={'allowed_books': allowed_books, 'max_quantities': max_quantities}
        )
        req_form = ReturnRequestForm()

    return render(request, "orders/request_return.html", {
        "formset": formset,
        "order": order,
        "req_form": req_form,
        # For template display, pair each form with the related order item
        "forms_and_items": zip(formset.forms, order.items.all()),
    })

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    now = timezone.now()
    for order in orders:
        order.can_return = order.status == "PAID" and (now - order.created_at) <= timedelta(days=14)
        order.return_expired = order.status == "PAID" and (now - order.created_at) > timedelta(days=14)

    return render(request, 'orders/order_history.html', {'orders': orders})

@login_required
def return_history(request):
    returns = ReturnRequest.objects.filter(order__user=request.user).order_by('-created_at')
    return render(request, 'orders/return_history.html', {'returns': returns})
