from unittest.mock import patch, Mock
from django.test import TestCase, override_settings
import requests
from myshop.books.models import Book
from . import import_books


class ImportSafetyTests(TestCase):
    def setUp(self):
        self.existing = Book.objects.create(title="Existing", authors="Demo Author", price=10)

    @override_settings(EXTERNAL_SERVICES_ENABLED=True)
    @patch("data.import_books.requests.get")
    def test_rate_limit_keeps_existing_catalogue(self, get):
        get.return_value.raise_for_status.side_effect = requests.HTTPError("429")
        with self.assertRaises(requests.HTTPError):
            import_books.import_books()
        self.assertTrue(Book.objects.filter(pk=self.existing.pk).exists())
        self.assertEqual(get.call_args.kwargs["timeout"], 15)

    @override_settings(EXTERNAL_SERVICES_ENABLED=True)
    @patch("data.import_books.requests.get", side_effect=requests.Timeout)
    def test_timeout_keeps_existing_catalogue(self, get):
        with self.assertRaises(requests.Timeout):
            import_books.import_books()
        self.assertTrue(Book.objects.filter(pk=self.existing.pk).exists())

    @patch("data.import_books.TOPICS", [("demo", "demo", "educational")])
    @patch("data.import_books.fetch_books")
    def test_repeated_import_does_not_duplicate_or_replace_prices(self, fetch):
        fetch.return_value = [{"volumeInfo": {"title": "Imported demo", "authors": ["Demo Author"], "language": "en"}}]
        import_books.import_books()
        imported = Book.objects.get(title="Imported demo")
        old_price = imported.price
        import_books.import_books()
        self.assertEqual(Book.objects.count(), 2)
        imported.refresh_from_db()
        self.assertEqual(imported.price, old_price)

    @override_settings(EXTERNAL_SERVICES_ENABLED=True)
    @patch("data.import_books.requests.get")
    def test_error_payload_is_not_an_empty_catalogue(self, get):
        get.return_value.json.return_value = {"error": {"message": "quota"}}
        with self.assertRaises(ValueError):
            import_books.fetch_books("demo")
