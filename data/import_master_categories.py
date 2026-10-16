import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myshop.settings")
django.setup()

from myshop.books.models import Category

master_categories = [
    "Technology",
    "Novels",
    "Business",
    "Health & Medical",
    "Science",
    "Education",
    "Arts & Design",
    "Language & Literature",
    "Biography & Autobiography",
    "History & Politics",
    "Philosophy & Religion",
    "Social Sciences",
    "Lifestyle & Self-Help",
    "Library & Reference",
    "Other",
]

for name in master_categories:
    Category.objects.get_or_create(name=name)

print("✅ Categories imported.")
