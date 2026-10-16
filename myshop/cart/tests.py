from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from myshop.books.models import Book, Category
from myshop.cart.models import CartItem, WishlistItem
from decimal import Decimal

User = get_user_model()


class CartViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="pass123")
        self.category = Category.objects.create(name="Novels")
        self.book = Book.objects.create(
            title="Test Book",
            slug="test-book",
            price=10.00,
            stock_status="In Stock",
            category=self.category,
        )

    def test_cart_view_anonymous(self):
        session = self.client.session
        session["cart"] = {"test-book": 2}
        session.save()
        response = self.client.get(reverse("cart:cart_view"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Book")

    def test_cart_view_authenticated(self):
        CartItem.objects.create(user=self.user, book=self.book, quantity=2)
        self.client.login(username="testuser", password="pass123")
        response = self.client.get(reverse("cart:cart_view"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Book")

    def test_add_to_cart_post_authenticated(self):
        self.client.login(username="testuser", password="pass123")
        response = self.client.post(
            reverse("cart:add_to_cart", args=["test-book"]), {"quantity": 2}
        )
        self.assertRedirects(response, reverse("cart:cart_view"))
        self.assertTrue(
            CartItem.objects.filter(user=self.user, book=self.book).exists()
        )

    def test_update_cart_post_authenticated(self):
        CartItem.objects.create(user=self.user, book=self.book, quantity=1)
        self.client.login(username="testuser", password="pass123")
        response = self.client.post(
            reverse("cart:update_cart", args=["test-book"]),
            {"quantity": 3},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            CartItem.objects.get(user=self.user, book=self.book).quantity, 3
        )

    def test_remove_from_cart_authenticated(self):
        CartItem.objects.create(user=self.user, book=self.book, quantity=1)
        self.client.login(username="testuser", password="pass123")
        response = self.client.post(
            reverse("cart:remove_from_cart", args=["test-book"])
        )
        self.assertRedirects(response, reverse("cart:cart_view"))
        self.assertFalse(
            CartItem.objects.filter(user=self.user, book=self.book).exists()
        )

    def test_empty_cart_authenticated(self):
        CartItem.objects.create(user=self.user, book=self.book, quantity=1)
        self.client.login(username="testuser", password="pass123")
        response = self.client.post(reverse("cart:empty_cart"))
        self.assertRedirects(response, reverse("cart:cart_view"))
        self.assertFalse(CartItem.objects.filter(user=self.user).exists())

    def test_add_to_wishlist_authenticated(self):
        self.client.login(username="testuser", password="pass123")
        response = self.client.post(reverse("cart:add_to_wishlist", args=["test-book"]))
        self.assertRedirects(response, reverse("cart:wishlist_view"))
        self.assertTrue(
            WishlistItem.objects.filter(user=self.user, book=self.book).exists()
        )

    def test_remove_from_wishlist_authenticated(self):
        WishlistItem.objects.create(user=self.user, book=self.book)
        self.client.login(username="testuser", password="pass123")
        response = self.client.post(
            reverse("cart:remove_from_wishlist", args=["test-book"])
        )
        self.assertRedirects(response, reverse("cart:wishlist_view"))
        self.assertFalse(
            WishlistItem.objects.filter(user=self.user, book=self.book).exists()
        )

    def test_clear_wishlist_authenticated(self):
        WishlistItem.objects.create(user=self.user, book=self.book)
        self.client.login(username="testuser", password="pass123")
        response = self.client.post(reverse("cart:clear_wishlist"))
        self.assertRedirects(response, reverse("cart:wishlist_view"))
        self.assertFalse(WishlistItem.objects.filter(user=self.user).exists())

    def test_move_to_cart_from_wishlist(self):
        WishlistItem.objects.create(user=self.user, book=self.book)
        self.client.login(username="testuser", password="pass123")
        response = self.client.post(
            reverse("cart:move_to_cart_from_wishlist", args=["test-book"])
        )
        self.assertRedirects(response, reverse("cart:cart_view"))
        self.assertTrue(
            CartItem.objects.filter(user=self.user, book=self.book).exists()
        )
        self.assertFalse(
            WishlistItem.objects.filter(user=self.user, book=self.book).exists()
        )

    def test_add_all_to_cart_from_wishlist(self):
        WishlistItem.objects.create(user=self.user, book=self.book)
        self.client.login(username="testuser", password="pass123")
        response = self.client.post(reverse("cart:move_all_to_cart"))
        self.assertRedirects(response, reverse("cart:cart_view"))
        self.assertTrue(
            CartItem.objects.filter(user=self.user, book=self.book).exists()
        )

    def test_add_endpoints_reject_get_and_missing_csrf(self):
        strict = Client(enforce_csrf_checks=True)
        for name in ("cart:add_to_cart", "cart:add_to_wishlist"):
            url = reverse(name, args=[self.book.slug])
            self.assertEqual(self.client.get(url).status_code, 405)
            self.assertEqual(strict.post(url).status_code, 403)

    def test_quantity_bounds_and_malformed_json(self):
        url = reverse("cart:add_to_cart", args=[self.book.slug])
        for data in ({"quantity": 1000}, {"quantity": None}, []):
            response = self.client.post(url, data=data, content_type="application/json", HTTP_X_REQUESTED_WITH="XMLHttpRequest")
            self.assertFalse(response.json().get("success", False))
            self.assertEqual(self.client.session.get("cart", {}), {})
