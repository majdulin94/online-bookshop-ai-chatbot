import os
import sys
import django
import requests
import random
from django.utils.text import slugify
from dotenv import load_dotenv

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myshop.settings")
django.setup()
load_dotenv()

from myshop.books.models import Book
from django.conf import settings
from decimal import Decimal

# Topics: (search query, topic tag, book type)
TOPICS = [
    ("artificial intelligence basics", "AI_Basics", "educational"),
    ("advanced artificial intelligence", "AI_Advanced", "educational"),
    ("data analysis beginner", "Data_Intro", "educational"),
    ("data science advanced", "Data_Advanced", "educational"),
    ("frontend web development", "FullStack_Frontend", "educational"),
    ("backend web development", "FullStack_Backend", "educational"),
    ("web design ui", "WebDesign_UI", "educational"),
    ("web design ux", "WebDesign_UX", "educational"),

    ("romance novels", "Romance Novels", "novel"),
    ("horror books", "Horror Novels", "novel"),
    ("science fiction", "Science Fiction Novels", "novel"),
    ("adventure books", "Action and Adventure Novels", "novel"),
    ("thriller novels", "Thriller Novels", "novel"),
    ("mystery novels", "Mystery Novels", "novel"),
    ("fantasy novels", "Fantasy Novels", "novel"),
    ("inspiring biographies", "Biography Novels", "novel"),

    ("business management", "business", "educational"),
    ("psychology", "psychology", "educational"),
    ("philosophy", "philosophy", "educational"),
    ("health and wellness", "health", "educational"),
    ("education theory", "education", "educational"),
    ("history of europe", "history", "educational"),
    ("language learning", "language", "educational"),
    ("religion and spirituality", "religion", "educational"),
    ("self-help and personal growth", "self-help", "educational"),
    ("library science", "library", "educational"),
]

# Default image if no thumbnail available
DEFAULT_THUMBNAIL = "/static/images/placeholder.jpg"

def fetch_books(query, start_index=0, max_results=40):
    if not settings.EXTERNAL_SERVICES_ENABLED:
        raise RuntimeError("External imports are disabled in isolated validation.")
    response = requests.get(
        "https://www.googleapis.com/books/v1/volumes",
        params={"q": query, "startIndex": start_index, "maxResults": max_results,
                "langRestrict": "en", "printType": "books"}, timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or "error" in payload or not isinstance(payload.get("items", []), list):
        raise ValueError("Invalid Google Books response")
    return payload.get("items", [])


def generate_unique_slug(title, topic_tag, existing_slugs, max_length=100):
    # 1. Create the base slug
    orig_slug = slugify(f"{title}-{topic_tag}" if topic_tag else title)
    # 2. Trim the base slug to leave space for a number later (e.g., "-99")
    base_slug = orig_slug[:max_length-5]  # allows for up to -9999
    slug = base_slug
    i = 2
    # 3. Repeat until you get a slug that does not exist
    while slug in existing_slugs:
        suffix = f"-{i}"
        # Trim to ensure it doesn't exceed the max length
        slug = (base_slug[:max_length-len(suffix)] + suffix)[:max_length]
        i += 1
    existing_slugs.add(slug)
    return slug


def import_books():
    # Keep all existing catalogue records and related user data.

    total_added, total_skipped = 0, 0
    existing_slugs = set(Book.objects.values_list("slug", flat=True))

    for query, topic_tag, book_type in TOPICS:
        topic_added = 0
        print(f"🔍 Importing topic: {topic_tag}")

        for start in range(0, 200, 40):
            items = fetch_books(query, start_index=start)
            for item in items:
                if not isinstance(item, dict) or not isinstance(item.get("volumeInfo"), dict):
                    total_skipped += 1
                    continue
                info = item["volumeInfo"]

                if not isinstance(info.get("title", ""), str) or not isinstance(info.get("authors", []), list):
                    total_skipped += 1
                    continue
                title = info.get("title", "").strip()
                authors = ", ".join(info.get("authors", []))
                publisher = info.get("publisher", "")
                published_date = info.get("publishedDate", "")
                description = info.get("description", "") or "No description available."
                thumbnail = info.get("imageLinks", {}).get("thumbnail", "") or DEFAULT_THUMBNAIL
                raw_categories = ", ".join(info.get("categories", []))
                language = info.get("language", "").lower()

                if language != "en" or not title or not authors:
                    total_skipped += 1
                    continue

                if len(title) > 255 or len(authors) > 255 or len(publisher) > 255 or len(raw_categories) > 255:
                    total_skipped += 1
                    continue

                base_price = random.randint(10, 30)
                cents = random.choice([0.00, 0.99])
                price = Decimal(str(round(base_price + cents, 2)))
                stock_status = random.choice(['In Stock', 'Limited Stock', 'Out of Stock'])

                if Book.objects.filter(title=title, authors=authors, topic_tag=topic_tag).exists():
                    total_skipped += 1
                    continue

                # Use the unique slug generation function
                slug = generate_unique_slug(title, topic_tag, existing_slugs)

                _, created = Book.objects.get_or_create(
                    title=title, authors=authors, topic_tag=topic_tag,
                    defaults={"publisher": publisher, "published_date": published_date,
                        "description": description, "thumbnail": thumbnail, "price": price,
                        "book_type": book_type, "slug": slug, "raw_categories": raw_categories,
                        "stock_status": stock_status},
                )

                if created:
                    total_added += 1
                    topic_added += 1

        print(f"✅ {topic_tag}: {topic_added} added, {total_skipped} skipped\n")

    print(f"🎉 DONE: {total_added} books added, {total_skipped} skipped\n")

if __name__ == "__main__":
    import_books()
