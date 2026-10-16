from itertools import count
from django.shortcuts import render
from myshop.books.models import Book, Category
from django.db.models import Count


def home(request):
    # Titles for Featured Books and Latest Arrivals
    featured_books_titles = [
        "AI Basics",
        "Full Stack Django and React",
        "Canadian Fiction",
    ]
    latest_arrivals_titles = ["Flow", "Nomics", "Mentopolis"]

    # Get featured books based on selected titles
    featured_books = Book.objects.filter(title__in=featured_books_titles)

    # Remove duplicates in featured books (if any)
    unique_featured_books = []
    seen_featured_titles = set()
    for book in featured_books:
        if book.title not in seen_featured_titles:
            unique_featured_books.append(book)
            seen_featured_titles.add(book.title)

    # Get latest books based on selected titles
    latest_books = Book.objects.filter(title__in=latest_arrivals_titles)

    # Remove duplicates in latest books (if any)
    unique_latest_books = []
    seen_latest_titles = set()
    for book in latest_books:
        if book.title not in seen_latest_titles:
            unique_latest_books.append(book)
            seen_latest_titles.add(book.title)

    # Top 8 categories by number of books
    #homepage_categories = Category.objects.annotate(book_count=Count("books")).order_by(
    #    "-book_count"
    #)[:8]

    homepage_categories = Category.objects.filter(
        name__in=[
            "Novels",
            "Technology",
            "Social Sciences",
            "Arts & Design",
            "Philosophy & Religion",
            "History & Politics",
            "Language & Literature",
            "Health & Medical"
        ]
    )

    category_images = {
        "Technology": "technology.jpg",
        "Novels": "novels.jpg",
        "Business": "business.jpg",
        "Health & Medical": "health-medical.jpg",
        "Science": "science.jpg",
        "Education": "education.jpg",
        "Arts & Design": "arts-design.jpg",
        "Language & Literature": "language-literature.jpg",
        "Biography & Autobiography": "biography-autobiography.jpg",
        "History & Politics": "history-politics.jpg",
        "Philosophy & Religion": "philosophy-religion.jpg",
        "Social Sciences": "social-sciences.jpg",
        "Lifestyle & Self-Help": "lifestyle-self-help.jpg",
        "Library & Reference": "library-reference.jpg",
        "Other": "other.jpg",
    }

    # Render the template with the books data
    return render(
        request,
        "core/home.html",
        {
            "featured_books": unique_featured_books,
            "latest_books": unique_latest_books,
            "homepage_categories": homepage_categories,
            "category_images": category_images,
        },
    )
