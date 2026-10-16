from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from myshop.books.models import Book
from bookreviews.models import Review

class ReviewViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.book = Book.objects.create(
            title="Test Book",
            slug="test-book",
            authors="Author A",
            published_date="2024-01-01",
            price=9.99,
            stock_status="In Stock",
        )
        self.review = Review.objects.create(
            book=self.book,
            user=self.user,
            comment="Initial review",
            rating=4,
            created_at=timezone.now(),
        )
        self.add_url = reverse("bookreviews:add_review", kwargs={"slug": self.book.slug})
        self.delete_url = reverse("bookreviews:delete_review", kwargs={"slug": self.book.slug})
        self.like_url = reverse("bookreviews:like_review", kwargs={"review_id": self.review.id})
        self.dislike_url = reverse("bookreviews:dislike_review", kwargs={"review_id": self.review.id})

    def test_add_review_requires_login(self):
        response = self.client.get(self.add_url)
        self.assertEqual(response.status_code, 302)  # redirect to login
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_add_review_post_valid_data_updates_existing_review(self):
        self.client.login(username="testuser", password="testpass")
        data = {
            "comment": "Updated review content",
            "rating": 5,
        }
        response = self.client.post(self.add_url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.review.refresh_from_db()
        self.assertEqual(self.review.comment, "Updated review content")
        self.assertEqual(self.review.rating, 5)

    def test_delete_review(self):
        self.client.login(username="testuser", password="testpass")
        response = self.client.post(self.delete_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Review.objects.filter(id=self.review.id).exists())

    def test_like_review_adds_like_and_removes_dislike(self):
        self.client.login(username="testuser", password="testpass")
        self.review.dislikes.add(self.user)
        response = self.client.post(self.like_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.review.refresh_from_db()
        self.assertIn(self.user, self.review.likes.all())
        self.assertNotIn(self.user, self.review.dislikes.all())

    def test_dislike_review_adds_dislike_and_removes_like(self):
        self.client.login(username="testuser", password="testpass")
        self.review.likes.add(self.user)
        response = self.client.post(self.dislike_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.review.refresh_from_db()
        self.assertIn(self.user, self.review.dislikes.all())
        self.assertNotIn(self.user, self.review.likes.all())
    def test_mutations_reject_get(self):
        self.client.force_login(self.user)
        for url in (self.delete_url, self.like_url, self.dislike_url):
            self.assertEqual(self.client.get(url).status_code, 405)

    def test_rating_bounds_are_validated_on_both_review_routes(self):
        self.client.force_login(self.user)
        for url in (self.add_url, reverse("books:book_detail", args=[self.book.slug])):
            for rating in (0, 6, 999):
                self.client.post(url, {"rating": rating, "comment": "invalid"})
                self.review.refresh_from_db()
                self.assertEqual(self.review.rating, 4)
