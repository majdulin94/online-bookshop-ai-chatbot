from django.urls import path
from .views import chatbot_api
from chatbot import views

urlpatterns = [
    path("api/", chatbot_api, name="chatbot_api"),
    path("history/", views.chat_history, name="chat_history"),
]
