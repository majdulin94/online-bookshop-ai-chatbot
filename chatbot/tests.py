from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from myshop.books.models import Book, Category
from chatbot.models import ChatSession, ChatMessage
import json


class ChatbotApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Novels")
        self.book = Book.objects.create(
            title="Love in the Time of AI",
            authors="Jane Bot",
            category=self.category,
            topic_tag="Romance Novels",
            slug="love-in-ai",
            price=19.99,
            stock_status="In Stock",
        )
        self.url = reverse("chatbot_api")

    def test_post_empty_message_returns_400(self):
        response = self.client.post(
            self.url, data=json.dumps({"message": ""}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_post_non_json_returns_400(self):
        response = self.client.post(
            self.url, data="notjson", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_basic_book_search_returns_book(self):
        response = self.client.post(
            self.url,
            data=json.dumps({"message": "romance novels"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("books", response.json())
        self.assertGreaterEqual(len(response.json()["books"]), 1)

    def test_category_request_returns_books(self):
        response = self.client.post(
            self.url,
            data=json.dumps({"message": "Novels"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["reply"].startswith("Here are some books from"), True
        )
        self.assertIn("books", response.json())

    def test_topic_question_returns_quick_replies(self):
        response = self.client.post(
            self.url,
            data=json.dumps({"message": "what book topics are available"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("quick_replies", response.json())

    def test_emotional_message_returns_recommendations(self):
        response = self.client.post(
            self.url,
            data=json.dumps({"message": "I'm feeling sad today"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("reply", response.json())
        self.assertIn("sentiment", response.json())

    def test_chat_message_is_logged(self):
        response = self.client.post(
            self.url,
            data=json.dumps({"message": "romance novels"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ChatSession.objects.exists())
        session = ChatSession.objects.first()
        self.assertTrue(
            ChatMessage.objects.filter(session=session, role="user").exists()
        )
        self.assertTrue(
            ChatMessage.objects.filter(session=session, role="assistant").exists()
        )
