from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from myshop.books.models import Book, Category
from myshop.cart.models import CartItem
from orders.models import Order, OrderItem, ReturnRequest, ReturnRequestItem
from datetime import timedelta

User = get_user_model()


class OrderViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="pass123", email="test@example.test"
        )
        self.category = Category.objects.create(name="Technology")
        self.book = Book.objects.create(
            title="Test Book",
            slug="test-book",
            price=20.00,
            stock_status="In Stock",
            category=self.category,
        )
        self.place_order_url = reverse("orders:place_order")
        self.guest_place_order_url = reverse("orders:guest_place_order")

    def test_place_order_cart_empty_redirects(self):
        self.client.login(username="testuser", password="pass123")
        response = self.client.post(self.place_order_url, follow=True)
        self.assertRedirects(response, reverse("cart:cart_view"))
        self.assertContains(response, "Your cart is empty.")

    def test_place_order_success_creates_order(self):
        self.client.login(username="testuser", password="pass123")
        CartItem.objects.create(user=self.user, book=self.book, quantity=1)
        data = {
            "address_line1": "Street 1",
            "address_line2": "",
            "city": "Berlin",
            "postal_code": "12345",
            "country": "Germany",
            "phone": "123456789",
        }
        response = self.client.post(self.place_order_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "orders/stripe_checkout.html")
        self.assertTrue(Order.objects.filter(user=self.user).exists())

    def test_guest_place_order_creates_user_and_order(self):
        session = self.client.session
        session["cart"] = {"test-book": 1}
        session.save()
        data = {
            "email": "guest@example.test",
            "password": "guestpass123",
            "address_line1": "Straße 1",
            "address_line2": "",
            "city": "Berlin",
            "postal_code": "10000",
            "country": "Germany",
            "phone": "123456789",
        }
        response = self.client.post(self.guest_place_order_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "orders/stripe_checkout.html")
        self.assertTrue(User.objects.filter(username="guest@example.test").exists())
        self.assertTrue(
            Order.objects.filter(user__username="guest@example.test").exists()
        )

    def test_unverified_payment_does_not_mark_paid_or_clear_cart(self):
        self.client.login(username="testuser", password="pass123")
        CartItem.objects.create(user=self.user, book=self.book, quantity=1)
        order = Order.objects.create(user=self.user, status="PENDING", total_price=20)
        OrderItem.objects.create(
            order=order, book=self.book, quantity=1, total_price=20
        )
        session = self.client.session
        session["pending_order_id"] = order.id
        session.save()
        response = self.client.get(reverse("orders:payment_success"))
        self.assertEqual(response.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, "PENDING")
        self.assertTrue(CartItem.objects.filter(user=self.user).exists())

    def test_payment_cancel_redirects(self):
        self.client.login(username="testuser", password="pass123")
        response = self.client.get(reverse("orders:payment_cancel"), follow=True)
        self.assertRedirects(response, reverse("cart:cart_view"))

    def test_order_history_shows_paid_orders_and_return_flags(self):
        self.client.login(username="testuser", password="pass123")
        paid_order = Order.objects.create(
            user=self.user,
            status="PAID",
            total_price=20,
            created_at=timezone.now() - timedelta(days=10),
        )
        expired_order = Order.objects.create(
            user=self.user,
            status="PAID",
            total_price=20,
            created_at=timezone.now() - timedelta(days=20),
        )
        paid_order.created_at = timezone.now() - timedelta(days=10)
        paid_order.save()
        expired_order.created_at = timezone.now() - timedelta(days=20)
        expired_order.save()
        response = self.client.get(reverse("orders:order_history"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Paid")
        orders = response.context["orders"]
        by_id = {order.pk: order for order in orders}
        self.assertTrue(by_id[paid_order.pk].can_return)
        self.assertTrue(by_id[expired_order.pk].return_expired)

    def test_return_request_view_allows_within_14_days(self):
        self.client.login(username="testuser", password="pass123")
        order = Order.objects.create(
            user=self.user,
            status="PAID",
            total_price=20,
            created_at=timezone.now() - timedelta(days=10),
        )
        OrderItem.objects.create(
            order=order, book=self.book, quantity=1, total_price=20
        )
        url = reverse("orders:request_return", args=[order.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "orders/request_return.html")

    def test_return_request_rejected_after_14_days(self):
        self.client.login(username="testuser", password="pass123")
        order = Order.objects.create(
            user=self.user,
            status="PAID",
            total_price=20,
        )
        order.created_at = timezone.now() - timedelta(days=20)
        order.save()
        OrderItem.objects.create(
            order=order, book=self.book, quantity=1, total_price=20
        )
        url = reverse("orders:request_return", args=[order.id])
        response = self.client.get(url)
        self.assertTemplateUsed(response, "orders/return_not_allowed.html")
