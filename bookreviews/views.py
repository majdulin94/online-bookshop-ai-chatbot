from django.views.decorators.http import require_POST
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Review
from .forms import ReviewForm
from myshop.books.models import Book


@login_required
def add_review(request, slug):
    book = get_object_or_404(Book, slug=slug)
    user_review = Review.objects.filter(book=book, user=request.user).first()

    if request.method == "POST":
        form = ReviewForm(request.POST, instance=user_review)
        if form.is_valid():
            review = form.save(commit=False)
            review.book = book
            review.user = request.user
            review.created_at = timezone.now()
            review.save()
            messages.success(request, "Your review has been submitted.")
            return redirect("books:book_detail", slug=slug)
    else:
        form = ReviewForm(instance=user_review)

    return render(request, "bookreviews/review_form.html", {
        "form": form,
        "book": book,
        "user_review": user_review,
    })


@login_required
@require_POST
def delete_review(request, slug):
    book = get_object_or_404(Book, slug=slug)
    review = Review.objects.filter(book=book, user=request.user).first()
    if review:
        review.delete()
        messages.success(request, "Your review has been deleted.")
    return redirect("books:book_detail", slug=slug)


@login_required
@require_POST
def like_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    if request.user in review.dislikes.all():
        review.dislikes.remove(request.user)
    review.likes.add(request.user)
    return redirect("books:book_detail", slug=review.book.slug)


@login_required
@require_POST
def dislike_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    if request.user in review.likes.all():
        review.likes.remove(request.user)
    review.dislikes.add(request.user)
    return redirect("books:book_detail", slug=review.book.slug)
