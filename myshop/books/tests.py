import warnings
from django.core.paginator import UnorderedObjectListWarning
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from myshop.books.models import Book, Category
from bookreviews.models import Review
from datetime import date

User = get_user_model()


class BookViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Novels")
        self.book = Book.objects.create(
            title="Love in the Time of AI",
            authors="Jane Bot",
            category=self.category,
            topic_tag="Romance Novels",
            slug="love-in-ai",
            price=19.99,
            stock_status="In Stock",
        )
        self.book_url = reverse("books:book_detail", args=[self.book.slug])
        self.list_url = reverse("books:book_list")

        warnings.filterwarnings(
            "ignore", category=UnorderedObjectListWarning, module=r".*books\.views"
        )

    def test_book_list_page_loads(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "books/book_list.html")
        self.assertContains(response, self.book.title)

    def test_book_list_filter_by_query(self):
        response = self.client.get(self.list_url + "?q=love")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.book.title)

    def test_book_list_filter_by_category_and_topic(self):
        response = self.client.get(
            self.list_url + "?category=Novels&topic=Romance+Novels"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.book.title)

    def test_book_list_excludes_out_of_stock(self):
        self.book.stock_status = "Out of Stock"
        self.book.save()
        response = self.client.get(self.list_url + "?in_stock=1")
        self.assertNotContains(response, self.book.title)

    def test_book_detail_view_anonymous(self):
        response = self.client.get(self.book_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "books/book_detail.html")
        self.assertContains(response, self.book.title)

    def test_book_detail_view_authenticated_user_can_review(self):
        user = User.objects.create_user(username="reviewer", password="pass123")
        self.client.login(username="reviewer", password="pass123")

        review_data = {
            "rating": 5,
            "comment": "Fantastic read!",
        }
        response = self.client.post(self.book_url, review_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fantastic read!")

        # Review was saved
        self.assertTrue(Review.objects.filter(book=self.book, user=user).exists())

    def test_book_detail_authenticated_user_can_delete_review(self):
        user = User.objects.create_user(username="deleter", password="pass123")
