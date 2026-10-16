"""Load the reviewed public catalogue without importing private database tables."""
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from myshop.books.models import Book, Category


class Command(BaseCommand):
    help = "Add the original public book catalogue without modifying existing books."

    @transaction.atomic
    def handle(self, *args, **options):
        data_dir = Path(__file__).resolve().parents[4] / "data"
        rows = json.loads((data_dir / "public_catalogue.json").read_text(encoding="utf-8"))
        category_names = json.loads((data_dir / "public_categories.json").read_text(encoding="utf-8"))
        fields = ("title", "authors", "published_date", "publisher", "description",
                  "thumbnail", "price", "book_type", "topic_tag", "slug",
                  "raw_categories", "stock_status")
        categories = {}
        for name in category_names:
            categories[name], _ = Category.objects.get_or_create(name=name)
        existing = set(Book.objects.values_list("slug", flat=True))
        books = [Book(**{field: row[field] for field in fields},
                      category=categories.get(row["category"]))
                 for row in rows if row["slug"] not in existing]
        Book.objects.bulk_create(books, batch_size=200)
        self.stdout.write(self.style.SUCCESS(
            f"Public catalogue ready: {len(books)} added; {len(rows) - len(books)} existing records preserved."))
