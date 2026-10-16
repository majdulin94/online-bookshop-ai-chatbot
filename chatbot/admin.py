from django.contrib import admin
from .models import ChatSession, ChatMessage, ConversationContext

admin.site.register(ChatSession)
admin.site.register(ChatMessage)
admin.site.register(ConversationContext)
