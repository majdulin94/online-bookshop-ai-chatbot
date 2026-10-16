from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from datetime import timedelta
from django.utils import timezone
from myshop.accounts.tokens import account_activation_token
from chatbot.models import ChatSession
from myshop.accounts.models import Profile

User = get_user_model()


class AccountsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse("register")
        self.profile_url = reverse("profile")
        self.edit_profile_url = reverse("edit_profile")
        self.logout_url = reverse("logout")

    def test_register_valid_post_sends_email_and_inactivates_user(self):
        data = {
            "username": "testuser",
            "email": "test@example.test",
            "password1": "StrongPassword123!",
            "password2": "StrongPassword123!",
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/registration_pending.html")

        user = User.objects.get(username="testuser")
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Aktiviere deinen Account", mail.outbox[0].subject)

    def test_register_invalid_post_shows_form_again(self):
        data = {
            "username": "",
            "email": "invalidemail",
            "password1": "x",
            "password2": "y",
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/register.html")

    def test_activation_success(self):
        user = User.objects.create_user(
            username="actuser", email="activation@example.test", password="x", is_active=False
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = account_activation_token.make_token(user)
        url = reverse("activate", args=[uid, token])
        response = self.client.get(url)
        self.assertTemplateUsed(response, "accounts/activation_success.html")
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_activation_invalid(self):
        url = reverse("activate", args=["invalid", "invalid-token"])
        response = self.client.get(url)
        self.assertTemplateUsed(response, "accounts/activation_invalid.html")

    def test_profile_requires_login(self):
        response = self.client.get(self.profile_url)
        self.assertRedirects(response, f"/accounts/login/?next={self.profile_url}")

    def test_edit_profile_requires_login(self):
        response = self.client.get(self.edit_profile_url)
        self.assertRedirects(response, f"/accounts/login/?next={self.edit_profile_url}")

    def test_profile_view_authenticated(self):
        user = User.objects.create_user(username="tester", password="test123")
        self.client.login(username="tester", password="test123")
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/profile.html")

    def test_edit_profile_post_success(self):
        user = User.objects.create_user(
            username="edituser",
            email="edit@example.test",
            password="test123",
            first_name="OldName",
        )
        self.client.login(username="edituser", password="test123")
        profile = user.profile

        data = {
            "username": "edituser",
            "email": "changed@example.test",
            "first_name": "NewName",
            "birthday": "2000-01-01",
        }

        response = self.client.post(self.edit_profile_url, data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.profile_url)

        user.refresh_from_db()
        profile.refresh_from_db()
        self.assertEqual(user.email, "changed@example.test")
        self.assertEqual(user.first_name, "NewName")
        self.assertEqual(str(profile.birthday), "2000-01-01")

    def test_logout_marks_chat_sessions_expired(self):
        user = User.objects.create_user(username="logoutuser", password="test123")
        session = ChatSession.objects.create(
            user=user,
            status="active",
            created_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=1),
        )
        self.client.login(username="logoutuser", password="test123")
        response = self.client.post(self.logout_url)
        self.assertRedirects(response, reverse("home"))

        session.refresh_from_db()
        self.assertEqual(session.status, "expired")

    def test_logout_rejects_get(self):
        self.assertEqual(self.client.get(self.logout_url).status_code, 405)
