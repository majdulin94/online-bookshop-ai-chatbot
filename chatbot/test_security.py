import json
from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from .models import ChatSession, ChatMessage, ConversationContext
from .session import get_or_create_session, summarize_session


class ChatSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="owner")
        self.session = ChatSession.objects.create(user=self.user, expires_at=timezone.now() + timedelta(days=1))
        ConversationContext.objects.create(session=self.session, summary="old preferences")
        ChatMessage.objects.create(session=self.session, role="user", content="Private book preference")
        self.history = reverse("chat_history")

    def test_history_requires_matching_owner(self):
        url = self.history + "?session_id=" + str(self.session.session_id)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(User.objects.create_user(username="other"))
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.user)
        self.assertContains(self.client.get(url), "Private book preference")
        self.assertEqual(self.client.get(self.history + "?session_id=bad-uuid").status_code, 404)

    def test_guest_history_requires_matching_browser_session(self):
        owned = self.client.get(self.history).json()["session_id"]
        self.assertEqual(self.client.get(self.history + "?session_id=" + owned).status_code, 200)
        self.assertEqual(Client().get(self.history + "?session_id=" + owned).status_code, 404)

    def test_csrf_is_required_and_history_supplies_cookie(self):
        client = Client(enforce_csrf_checks=True)
        url = reverse("chatbot_api")
        self.assertEqual(client.post(url, {"message": "Novels"}, content_type="application/json").status_code, 403)
        client.get(self.history)
        token = client.cookies["csrftoken"].value
        response = client.post(url, {"message": "Novels"}, content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)

    def test_malformed_filter_and_message_inputs(self):
        for data in [{"message": "x" * 2001}, {"message": [1]}, [],
                     {"message": "books", "price_filter": []},
                     {"message": "books", "price_filter": {"min": "NaN"}},
                     {"message": "books", "rating_filter": {"min": -1}},
                     {"message": "books", "stock_status": [1]}]:
            with self.subTest(data=str(data)[:70]):
                self.assertEqual(self.client.post(reverse("chatbot_api"), data=json.dumps(data), content_type="application/json").status_code, 400)

    @override_settings(CHAT_REQUESTS_PER_MINUTE=1)
    def test_chat_is_rate_limited(self):
        self.assertEqual(self.client.post(reverse("chatbot_api"), {"message": "Novels"}, content_type="application/json").status_code, 200)
        self.assertEqual(self.client.post(reverse("chatbot_api"), {"message": "Novels"}, content_type="application/json").status_code, 429)

    @patch("chatbot.session.ai_provider.get_chat_response", return_value=("likes Python", None))
    def test_expiry_carries_summary_without_duplicate_provider_calls(self, provider):
        self.session.expires_at = timezone.now() - timedelta(seconds=1)
        self.session.save()
        new = get_or_create_session(self.user)
        self.assertEqual(new.conversationcontext.summary, "likes Python")
        self.assertEqual(provider.call_count, 1)

    @patch("chatbot.session.ai_provider.get_chat_response", return_value=("Neutral", {"unavailable": True}))
    def test_service_failure_preserves_summary(self, provider):
        self.assertEqual(summarize_session(self.session), "old preferences")
        self.session.conversationcontext.refresh_from_db()
        self.assertEqual(self.session.conversationcontext.summary, "old preferences")

    @patch("openai.OpenAI")
    def test_isolated_provider_never_constructs_live_client(self, client):
        from .ai_providers.gpt_provider import GPTProvider
        result, meta = GPTProvider(api_key="test-placeholder", model="test").get_chat_response([])
        self.assertTrue(meta["unavailable"])
        client.assert_not_called()
