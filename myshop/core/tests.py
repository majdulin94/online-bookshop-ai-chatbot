from django.test import TestCase, Client
from django.urls import reverse
from myshop.books.models import Book, Category


class HomeViewTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Kategorien für Startseite
        categories = [
            "Novels",
            "Technology",
            "Social Sciences",
            "Arts & Design",
            "Philosophy & Religion",
            "History & Politics",
            "Language & Literature",
            "Health & Medical",
        ]
        for name in categories:
            Category.objects.create(name=name)

        # Featured
        Book.objects.create(title="AI Basics", slug="ai-basics", price=9.99)
        Book.objects.create(
            title="Full Stack Django and React", slug="fs-django-react", price=19.99
        )
        Book.objects.create(
            title="Canadian Fiction", slug="canadian-fiction", price=12.99
        )

        # Latest
        Book.objects.create(title="Flow", slug="flow", price=8.99)
        Book.objects.create(title="Nomics", slug="nomics", price=10.99)
        Book.objects.create(title="Mentopolis", slug="mentopolis", price=7.99)

    def test_home_view_status_ok(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")

    def test_featured_books_in_context(self):
        response = self.client.get(reverse("home"))
        featured = response.context["featured_books"]
        titles = [b.title for b in featured]
        self.assertIn("AI Basics", titles)
        self.assertIn("Full Stack Django and React", titles)
        self.assertIn("Canadian Fiction", titles)
        self.assertEqual(len(titles), 3)  # Sicher, dass keine Duplikate drin sind

    def test_latest_books_in_context(self):
        response = self.client.get(reverse("home"))
        latest = response.context["latest_books"]
        titles = [b.title for b in latest]
        self.assertIn("Flow", titles)
        self.assertIn("Nomics", titles)
        self.assertIn("Mentopolis", titles)
        self.assertEqual(len(titles), 3)

    def test_homepage_categories_in_context(self):
        response = self.client.get(reverse("home"))
        category_names = [cat.name for cat in response.context["homepage_categories"]]
        expected = [
            "Novels",
            "Technology",
            "Social Sciences",
            "Arts & Design",
            "Philosophy & Religion",
            "History & Politics",
            "Language & Literature",
            "Health & Medical",
        ]
        self.assertEqual(set(category_names), set(expected))

    def test_category_images_exist_in_context(self):
        response = self.client.get(reverse("home"))
        category_images = response.context["category_images"]
        self.assertIn("Technology", category_images)
        self.assertIn("Novels", category_images)
        self.assertIn("Social Sciences", category_images)
