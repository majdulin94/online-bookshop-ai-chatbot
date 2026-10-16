from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from myshop.books.models import Book
from myshop.cart.models import CartItem
from .models import Order, OrderItem, ReturnRequest, ReturnRequestItem


class PaymentSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="buyer", password="test-pass")
        self.client.force_login(self.user)
        self.book = Book.objects.create(title="Demo", price=Decimal("10.01"))
        self.order = Order.objects.create(user=self.user, total_price=Decimal("10.01"), stripe_session_id="cs_mock")
        OrderItem.objects.create(order=self.order, book=self.book, quantity=1, total_price=self.book.price)
        CartItem.objects.create(user=self.user, book=self.book, quantity=2)
        session = self.client.session
        session["pending_order_id"] = self.order.pk
        session["cart"] = {self.book.slug: 1}
        session.save()
        self.url = reverse("orders:payment_success") + "?session_id=cs_mock"

    def verified_payment(self):
        return {"id": "cs_mock", "payment_status": "paid", "status": "complete", "mode": "payment",
                "currency": "eur", "amount_total": int(self.order.payable_total * 100),
                "client_reference_id": str(self.order.pk)}

    def test_direct_success_cannot_mark_order_paid(self):
        self.assertEqual(self.client.get(reverse("orders:payment_success")).status_code, 400)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "PENDING")

    @override_settings(EXTERNAL_SERVICES_ENABLED=True)
    @patch("orders.views.stripe.checkout.Session.retrieve")
    def test_unpaid_wrong_amount_currency_reference_and_status_rejected(self, retrieve):
        for key, value in [("payment_status", "unpaid"), ("amount_total", 1), ("currency", "usd"),
                           ("client_reference_id", "other"), ("status", "open"), ("mode", "subscription")]:
            with self.subTest(key=key):
                payment = self.verified_payment()
                payment[key] = value
                retrieve.return_value = payment
                self.assertEqual(self.client.get(self.url).status_code, 400)
                self.order.refresh_from_db()
                self.assertEqual(self.order.status, "PENDING")

    @override_settings(EXTERNAL_SERVICES_ENABLED=True)
    @patch("orders.views.stripe.checkout.Session.retrieve")
    def test_verified_payment_is_idempotent_and_preserves_later_cart_additions(self, retrieve):
        retrieve.return_value = self.verified_payment()
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "PAID")
        self.assertEqual(CartItem.objects.get(user=self.user).quantity, 1)
        self.assertEqual(self.client.session["cart"], {})
        self.assertEqual(retrieve.call_count, 1)

    @override_settings(EXTERNAL_SERVICES_ENABLED=True)
    @patch("orders.views.stripe.checkout.Session.retrieve")
    def test_other_user_cannot_complete_payment(self, retrieve):
        self.client.force_login(User.objects.create_user(username="other"))
        self.assertEqual(self.client.get(self.url).status_code, 404)
        retrieve.assert_not_called()

    @override_settings(EXTERNAL_SERVICES_ENABLED=True)
    @patch("orders.views.stripe.checkout.Session.create")
    def test_checkout_uses_snapshot_and_rounds_cents(self, create):
        self.book.price = Decimal("99.99")
        self.book.save()
        create.return_value = SimpleNamespace(id="cs_new", url="https://checkout.stripe.com/mock")
        response = self.client.post(reverse("orders:create-checkout-session"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(create.call_args.kwargs["line_items"][0]["price_data"]["unit_amount"], 1661)
        self.order.refresh_from_db()
        self.assertEqual(self.order.stripe_session_id, "cs_new")

    @override_settings(EXTERNAL_SERVICES_ENABLED=True)
    @patch("orders.views.stripe.checkout.Session.create")
    def test_checkout_rejects_foreign_or_paid_pending_session(self, create):
        self.order.status = "PAID"
        self.order.save()
        self.assertEqual(self.client.post(reverse("orders:create-checkout-session")).status_code, 404)
        create.assert_not_called()

    def test_order_item_price_stays_frozen_after_book_price_change(self):
        item = self.order.items.get()
        self.book.price = Decimal("50")
        self.book.save()
        item.book = self.book
        item.save()
        item.refresh_from_db()
        self.assertEqual(item.total_price, Decimal("10.01"))

    def test_unavailable_or_unpriced_cart_does_not_create_order(self):
        before = Order.objects.count()
        for price, stock in [(None, "In Stock"), (Decimal("10"), "Out of Stock")]:
            self.book.price, self.book.stock_status = price, stock
            self.book.save()
            response = self.client.post(reverse("orders:place_order"), {
                "address_line1": "Demo street", "city": "Berlin", "postal_code": "10000", "country": "Germany"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(Order.objects.count(), before)

    def return_data(self, quantities):
        data = {"form-TOTAL_FORMS": len(quantities), "form-INITIAL_FORMS": 0,
                "form-MIN_NUM_FORMS": 0, "form-MAX_NUM_FORMS": 1000}
        for index, qty in enumerate(quantities):
            data[f"form-{index}-book"] = self.book.pk
            data[f"form-{index}-quantity"] = qty
        return data

    def test_returns_reject_unpaid_duplicate_rows_and_repeated_quantity(self):
        url = reverse("orders:request_return", args=[self.order.pk])
        self.client.post(url, self.return_data([1]))
        self.assertEqual(ReturnRequest.objects.count(), 0)
        self.order.status = "PAID"
        self.order.save()
        self.client.post(url, self.return_data([1, 1]))
        self.assertEqual(ReturnRequest.objects.count(), 0)
        self.client.post(url, self.return_data([1]))
        self.assertEqual(ReturnRequestItem.objects.count(), 1)
        self.client.post(url, self.return_data([1]))
        self.assertEqual(ReturnRequestItem.objects.count(), 1)

    def test_exact_return_deadline(self):
        self.order.status = "PAID"
        self.order.created_at = timezone.now() - timedelta(days=14, seconds=1)
        self.order.save()
        response = self.client.post(reverse("orders:request_return", args=[self.order.pk]), self.return_data([1]))
        self.assertTemplateUsed(response, "orders/return_not_allowed.html")

    def test_empty_guest_cart_and_weak_password_do_not_create_user(self):
        self.client.logout()
        data = {"email": "guest@example.test", "password": "UniquelyStrong123!", "address_line1": "Demo street",
                "city": "Berlin", "postal_code": "10000", "country": "Germany"}
        self.client.post(reverse("orders:guest_place_order"), data)
        self.assertFalse(User.objects.filter(username=data["email"]).exists())
        session = self.client.session
        session["cart"] = {self.book.slug: 1}
        session.save()
        data["password"] = "123456"
        self.client.post(reverse("orders:guest_place_order"), data)
        self.assertFalse(User.objects.filter(username=data["email"]).exists())

    def test_cart_totals_must_fit_order_storage(self):
        from .views import valid_cart
        self.book.price = Decimal("999999.99")
        self.assertTrue(valid_cart([(self.book, 1)]))
        self.assertFalse(valid_cart([(self.book, 2)]))
