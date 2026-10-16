"""HTTP smoke checks against a running server using myshop.test_settings only.

Run from the repository root: python scripts/smoke_test.py
The server must already be running on 127.0.0.1:8765.
"""
import os
from secrets import token_urlsafe
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["DJANGO_SETTINGS_MODULE"] = "myshop.test_settings"
import django
django.setup()

import requests
from django.contrib.auth.models import User
from django.core.management import call_command
from django.urls import reverse
from myshop.books.models import Book

BASE = os.environ.get("BOOKSHOP_SMOKE_BASE_URL", "http://127.0.0.1:8765")
call_command("seed_demo", verbosity=0)
user, _ = User.objects.get_or_create(username="smoke-demo", defaults={"email": "demo@example.test"})
demo_password = token_urlsafe(24)
user.set_password(demo_password)
user.save()
book = Book.objects.filter(title="AI Basics").order_by("pk").first()
assert book is not None, "Public demo catalogue must contain AI Basics"
session = requests.Session()
passed = []


def get(name, status=200, args=None):
    response = session.get(BASE + reverse(name, args=args), timeout=10, allow_redirects=False)
    assert response.status_code == status, (name, response.status_code)
    passed.append(name)
    return response


def post(name, data=None, status=200, args=None, json=None):
    response = session.post(BASE + reverse(name, args=args), data=data, json=json,
        headers={"X-CSRFToken": session.cookies.get("csrftoken", "")}, timeout=10, allow_redirects=False)
    assert response.status_code == status, (name, response.status_code)
    passed.append(name)
    return response


get("home")
get("books:book_list")
get("books:book_detail", args=[book.slug])
get("login")
post("cart:add_to_cart", {"quantity": 1}, status=302, args=[book.slug])
get("cart:cart_view")
get("chat_history")
assert post("chatbot_api", json={"message": "Technology"}).json()["books"]
post("login", {"username": user.username, "password": demo_password}, status=302)
get("profile")
post("cart:add_to_cart", {"quantity": 1}, status=302, args=[book.slug])
post("cart:add_to_wishlist", status=302, args=[book.slug])
get("cart:wishlist_view")
post("bookreviews:add_review", {"rating": 5, "comment": "Synthetic smoke review."}, status=302, args=[book.slug])
get("orders:place_order")
post("orders:place_order", {"address_line1": "Demo street", "city": "Berlin", "postal_code": "10000", "country": "Germany"})
post("orders:create-checkout-session", status=503)
get("orders:payment_success", status=400)
get("orders:order_history")
get("orders:return_history")
post("logout", status=302)
print(f"PASS: {len(passed)} live HTTP checks, including expected payment safety rejections.")
