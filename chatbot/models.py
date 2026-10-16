import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from .config import SESSION_DURATION
from django.db.models import JSONField


class ChatSession(models.Model):
    """
    Represents a chat session for a user or guest.
    """
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    visitor_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    status = models.CharField(max_length=20, default="active")  # active, expired

    def is_expired(self):
        """Check if the session has expired."""
        return timezone.now() > self.expires_at

    def mark_expired(self):
        """Mark session as expired and trigger summary update."""
        if self.status != "expired":
            self.status = "expired"
            self.save()
            if self.user:
                from chatbot.session import summarize_session
                summarize_session(self)

    def extend_if_logged_in(self):
        """Extend expiry if the user is logged in and session is active."""
        if self.user and self.status == "active":
            self.expires_at = timezone.now() + SESSION_DURATION
            self.save()


class ChatMessage(models.Model):
    """
    Stores each message (user or assistant) in a chat session.
    """
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE)
    role = models.CharField(max_length=20)  # user / assistant
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    suggested_books = JSONField(null=True, blank=True)
    sentiment = models.CharField(max_length=32, null=True, blank=True)

    class Meta:
        ordering = ['timestamp']


class ConversationContext(models.Model):
    """
    Stores the running summary of a chat session.
    """
    session = models.OneToOneField(ChatSession, on_delete=models.CASCADE)
    summary = models.TextField(blank=True)
    summary_updated_at = models.DateTimeField(null=True, blank=True)
