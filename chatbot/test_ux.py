from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from chatbot.models import ChatMessage, ChatSession
from chatbot.views import analyze_sentiment
from chatbot.welcome_utils import get_dynamic_welcome
from myshop.books.models import Book, Category


class ChatbotUXTests(TestCase):
    def setUp(self):
        cache.clear()

    def assert_one_welcome(self, data):
        welcome = data['welcome_message']
        self.assertEqual(welcome.count('What are you in the mood for today?'), 1)
        self.assertEqual(welcome.count('•'), 3)
        self.assertIn('AI-assisted assistant', welcome)
        self.assertNotIn('show my orders', welcome)
        self.assertNotIn('how can i pay', welcome)
        self.assertNotIn('show my returns', welcome)
        self.assertNotIn('Try asking about books, topics, your orders', welcome)

    def test_new_guest_has_one_banner_and_no_stored_welcome(self):
        data = self.client.get(reverse('chat_history')).json()
        self.assert_one_welcome(data)
        self.assertEqual(data['messages'], [])
        self.assertEqual(ChatMessage.objects.count(), 0)
        repeated = self.client.get(reverse('chat_history'), {'session_id': data['session_id']}).json()
        self.assert_one_welcome(repeated)
        self.assertEqual(repeated['messages'], [])
        self.assertEqual(ChatSession.objects.count(), 1)

    def test_new_account_has_one_banner_without_account_name(self):
        user = User.objects.create_user(username='demo-owner')
        self.client.force_login(user)
        data = self.client.get(reverse('chat_history')).json()
        self.assert_one_welcome(data)
        self.assertNotIn(user.username, data['welcome_message'])
        self.assertEqual(data['all_sessions'][0]['messages'], [])
        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_legacy_stored_welcome_is_hidden_without_deleting_history(self):
        for authenticated in (False, True):
            with self.subTest(authenticated=authenticated):
                client = Client()
                if authenticated:
                    client.force_login(User.objects.create_user(username='legacy-demo'))
                client.get(reverse('chat_history'))
                session = ChatSession.objects.order_by('-pk').first()
                legacy = ('Good afternoon! <span>demo-owner</span><br>'
                          'Try asking about books, topics, your orders, or just share your feelings!<br>'
                          '• Show me some sci-fi novels<br>• Recommend books to learn Python<br>'
                          '• Give me a romantic story<br>• show my orders<br>• how can i pay<br>'
                          'What are you in the mood for today? 😊')
                ChatMessage.objects.create(session=session, role='assistant', content=get_dynamic_welcome())
                ChatMessage.objects.create(session=session, role='assistant', content=legacy)
                ChatMessage.objects.create(session=session, role='user', content='I feel happy')
                ChatMessage.objects.create(session=session, role='assistant', content='A real reply', sentiment='Positive')
                for params in ({}, {'session_id': str(session.session_id)}):
                    data = client.get(reverse('chat_history'), params).json()
                    messages = data.get('messages', data.get('all_sessions', [{}])[0].get('messages'))
                    self.assertEqual([m['content'] for m in messages], ['I feel happy', 'A real reply'])
                    self.assert_one_welcome(data)
                self.assertEqual(session.chatmessage_set.count(), 4)

    def test_ordinary_initial_assistant_reply_is_preserved(self):
        data = self.client.get(reverse('chat_history')).json()
        session = ChatSession.objects.get(session_id=data['session_id'])
        ChatMessage.objects.create(session=session, role='assistant', content='Good afternoon! Here are your books.')
        data = self.client.get(reverse('chat_history'), {'session_id': data['session_id']}).json()
        self.assertEqual(len(data['messages']), 1)
        self.assertNotIn('<img', get_dynamic_welcome('<img src=x onerror=alert(1)>'))

    @patch('chatbot.views.ai_provider.get_chat_response', return_value=('Neutral', {'unavailable': True}))
    def test_moods_reach_api_and_history_with_original_sentiment_classes(self, provider):
        for name, topic in [('Lifestyle & Self-Help', 'self-help'), ('Novels', 'Romance Novels'),
                            ('Business', 'business'), ('Science', 'Data_Intro'), ('Technology', 'AI_Basics')]:
            cat = Category.objects.create(name=name)
            Book.objects.create(title=name, category=cat, topic_tag=topic, price='19.99')
        cases = [
            ('I feel sad', 'Negative', 'Lifestyle & Self-Help'),
            ('I feel happy', 'Positive', 'Novels'),
            ("I'm bored", 'Neutral', 'Novels'),
            ('I feel very motivated to start a new project', 'Positive', 'Business'),
            ("I'm curious about new technologies", 'Positive', 'Science'),
            ("I'm curious about technology", 'Positive', 'Technology'),
            ("I'm feeling a bit down and bored today. Can you suggest some entertaining books?", 'Negative', 'Lifestyle & Self-Help'),
        ]
        for prompt, sentiment, category in cases:
            with self.subTest(prompt=prompt):
                provider.reset_mock()
                response = Client().post(reverse('chatbot_api'), {'message': prompt}, content_type='application/json')
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data['sentiment'], sentiment)
                self.assertTrue(data['books'])
                self.assertEqual(data['books'][0]['category'], category)
                self.assertEqual(ChatMessage.objects.filter(session__session_id=data['session_id'], role='assistant').last().sentiment, sentiment)
                self.assertEqual(provider.call_count, 1)

    @patch('chatbot.views.ai_provider.get_chat_response')
    def test_valid_provider_classification_remains_authoritative(self, provider):
        for value in ('Positive', 'Negative', 'Neutral'):
            provider.return_value = (value, None)
            self.assertEqual(analyze_sentiment('I feel happy'), value)

    @patch('chatbot.views.ai_provider.get_chat_response')
    def test_invalid_or_failed_provider_uses_mood_fallback(self, provider):
        for value in (('unrecognized', None), (None, None), ('Neutral', {'unavailable': True})):
            provider.return_value = value
            self.assertEqual(analyze_sentiment('I feel sad'), 'Negative')
            self.assertEqual(analyze_sentiment('I feel motivated'), 'Positive')
            self.assertEqual(analyze_sentiment("I'm bored"), 'Neutral')
        provider.side_effect = RuntimeError('service unavailable')
        self.assertEqual(analyze_sentiment('I feel happy'), 'Positive')
        self.assertEqual(analyze_sentiment('book recommendations'), 'Neutral')

    @patch('chatbot.views.ai_provider.get_chat_response', return_value=('Neutral', {'unavailable': True}))
    def test_fallback_matches_whole_mood_words(self, provider):
        self.assertEqual(analyze_sentiment('Download a book about blueshift'), 'Neutral')
        self.assertEqual(analyze_sentiment('I am unhappy'), 'Negative')
