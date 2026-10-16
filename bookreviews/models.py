from django.db import models
from django.contrib.auth.models import User
from myshop.books.models import Book

class Review(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(default=1)  # Bewertung von 1 bis 5 Sterne
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # NEU: Like/Dislike Felder
    likes = models.ManyToManyField(User, related_name='liked_reviews', blank=True)
    dislikes = models.ManyToManyField(User, related_name='disliked_reviews', blank=True)

    class Meta:
        unique_together = ('book', 'user')  # Ein Benutzer darf ein Buch nur einmal bewerten
        ordering = ['-created_at']  # Neueste Bewertungen zuerst

    def total_likes(self):
        return self.likes.count()

    def total_dislikes(self):
        return self.dislikes.count()

    def __str__(self):
        return f"{self.user.username} – {self.book.title} ({self.rating}★)"
