import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myshop.settings")
django.setup()

from myshop.books.models import Book, Category

category_mapping = {
    # Novel topics
    "Romance Novels": "Novels",
    "Horror Novels": "Novels",
    "Science Fiction Novels": "Novels",
    "Action and Adventure Novels": "Novels",
    "Thriller Novels": "Novels",
    "Mystery Novels": "Novels",
    "Fantasy Novels": "Novels",
    "Biography Novels": "Novels",

    # Educational topics
    "AI_Basics": "Technology",
    "AI_Advanced": "Technology",
    "FullStack_Frontend": "Technology",
    "FullStack_Backend": "Technology",
    "Data_Intro": "Science",
    "Data_Advanced": "Science",
    "WebDesign_UI": "Arts & Design",
    "WebDesign_UX": "Arts & Design",
    "business": "Business",
    "psychology": "Social Sciences",
    "philosophy": "Philosophy & Religion",
    "religion": "Philosophy & Religion",
    "health": "Health & Medical",
    "education": "Education",
    "history": "History & Politics",
    "language": "Language & Literature",
    "self-help": "Lifestyle & Self-Help",
    "library": "Library & Reference",
}

def get_master_category(tag):
    return category_mapping.get(tag.strip(), "Other")

updated = 0

for book in Book.objects.all():
    if not book.topic_tag:
        continue
    mapped = get_master_category(book.topic_tag)
    if mapped:
        category_obj, _ = Category.objects.get_or_create(name=mapped)
        if book.category != category_obj:
            book.category = category_obj
            book.save()
            updated += 1

print(f"✅ Updated {updated} books with master categories.")
