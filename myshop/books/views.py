from django.shortcuts import render, get_object_or_404
from .models import Book
from django.db.models import Q, Case, When, Value, IntegerField, Avg
from django.core.paginator import Paginator

from bookreviews.models import Review
from bookreviews.forms import ReviewForm
from django.utils import timezone


def book_list(request):
    query = request.GET.get("q", "")
    filter_type = request.GET.get("type", "")
    topic = request.GET.get("topic", "")
    category = request.GET.get("category", "")

    books = Book.objects.all().order_by("pk")

    # Categories and Topics
    categories = [
        "Technology",
        "Novels",
        "Business",
        "Science",
        "Health & Medical",
        "Education",
        "Arts & Design",
        "Language & Literature",
        "History & Politics",
        "Philosophy & Religion",
        "Social Sciences",
        "Lifestyle & Self-Help",
        "Library & Reference",
        "Other",
    ]
    topics_by_category = {
        "Technology": [
            "AI_Basics",
            "AI_Advanced",
            "FullStack_Frontend",
            "FullStack_Backend",
        ],
        "Novels": [
            "Romance Novels",
            "Horror Novels",
            "Science Fiction Novels",
            "Action and Adventure Novels",
            "Thriller Novels",
            "Mystery Novels",
            "Fantasy Novels",
            "Biography Novels",
        ],
        "Business": ["business"],
        "Health & Medical": ["health"],
        "Science": ["Data_Intro", "Data_Advanced"],
        "Education": ["education"],
        "Arts & Design": ["WebDesign_UI", "WebDesign_UX"],
        "Language & Literature": ["language"],
        "Biography & Autobiography": ["Biography Novels"],
        "History & Politics": ["history"],
        "Philosophy & Religion": ["philosophy", "religion"],
        "Social Sciences": ["psychology"],
        "Lifestyle & Self-Help": ["self-help"],
        "Library & Reference": ["library"],
        "Other": [],
    }

    # Search filter
    if query:
        books = (
            books.annotate(
                relevance=Case(
                    When(title__icontains=query, then=Value(6)),
                    When(authors__icontains=query, then=Value(5)),
                    When(category__name__icontains=query, then=Value(4)),
                    When(topic_tag__icontains=query, then=Value(3)),
                    When(publisher__icontains=query, then=Value(2)),
                    When(description__icontains=query, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
            .filter(
                Q(title__icontains=query)
                | Q(authors__icontains=query)
                | Q(category__name__icontains=query)
                | Q(topic_tag__icontains=query)
                | Q(publisher__icontains=query)
                | Q(description__icontains=query)
            )
            .order_by("-relevance")
        )

    # Filter by type
    if filter_type:
        books = books.filter(book_type=filter_type)

    # Filter by category and topic
    if category:
        books = books.filter(category__name__icontains=category)
        if topic:
            books = books.filter(topic_tag__iexact=topic)
    elif topic:
        books = books.filter(topic_tag__iexact=topic)

    if request.GET.get("in_stock") == "1":
        books = books.exclude(stock_status__iexact="Out of Stock")

    # Pagination
    paginator = Paginator(books, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Prepare category-topic mapping
    category_topic_list = [
        {"category": cat, "topics": topics_by_category.get(cat, [])}
        for cat in categories
    ]

    return render(
        request,
        "books/book_list.html",
        {
            "page_obj": page_obj,
            "query": query,
            "filter_type": filter_type,
            "selected_topic": topic,
            "selected_category": category,
            "categories": categories,
            "category_topic_list": category_topic_list,
        },
    )


def book_detail(request, slug):
    book = get_object_or_404(Book, slug=slug)
    avg_rating = Review.objects.filter(book=book).aggregate(avg=Avg("rating"))["avg"]
    user_review = None
    form = None

    if request.user.is_authenticated:
        user_review = Review.objects.filter(book=book, user=request.user).first()

        if request.method == "POST":
            if "delete_review" in request.POST:
                if user_review:
                    user_review.delete()
                    user_review = None
                    form = ReviewForm()
            else:
                form = ReviewForm(request.POST, instance=user_review)
                if form.is_valid():
                    review = form.save(commit=False)
                    review.book = book
                    review.user = request.user
                    review.created_at = timezone.now()
                    review.save()
                    user_review = review
                    form = ReviewForm(instance=review)
        else:
            form = ReviewForm(instance=user_review)

        reviews = (
            Review.objects.filter(book=book)
            .exclude(user=request.user)
            .order_by("-created_at")
        )
    else:
        reviews = Review.objects.filter(book=book).order_by("-created_at")

    return render(
        request,
        "books/book_detail.html",
        {
            "book": book,
            "user_review": user_review,
            "avg_rating": avg_rating,
            "reviews": reviews,
            "form": form,
        },
    )
