import json
import re

from django.conf import settings
from django.db.models import Q, Avg, Count
from django.http import JsonResponse, HttpRequest
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.core.exceptions import ValidationError
from django.core.cache import cache
import uuid
import math
from django.views.decorators.http import require_GET
from rapidfuzz import process
from .welcome_utils import get_dynamic_welcome
from chatbot.models import ChatSession, ChatMessage
from chatbot.session import get_or_create_session, summarize_session
from chatbot.config import OPENAI_MODEL, MAX_BOOKS
from myshop.books.models import Book

from chatbot.ai_providers.gpt_provider import GPTProvider

# === AI Provider Initialization ===
ai_provider = GPTProvider(api_key=settings.OPENAI_API_KEY, model=OPENAI_MODEL)

# === Categories, Topics, Synonyms (search configuration) ===
CATEGORIES = [
    "Technology", "Novels", "Business", "Health & Medical", "Science", "Education",
    "Arts & Design", "Language & Literature", "Biography & Autobiography", "History & Politics",
    "Philosophy & Religion", "Social Sciences", "Lifestyle & Self-Help", "Library & Reference", "Other"
]

topics_by_category = {
    "Technology": ["AI_Basics", "AI_Advanced", "FullStack_Frontend", "FullStack_Backend"],
    "Novels": [
        "Romance Novels", "Horror Novels", "Science Fiction Novels",
        "Action and Adventure Novels", "Thriller Novels",
        "Mystery Novels", "Fantasy Novels", "Biography Novels"
    ],
    "Business": ["business"],
    "Health & Medical": ["health"],
    "Science": ["Data_Intro", "Data_Advanced"],
    "Education": ["AI_Basics", "AI_Advanced", "FullStack_Frontend", "FullStack_Backend", "Data_Intro", "Data_Advanced"],
    "Arts & Design": ["WebDesign_UI", "WebDesign_UX"],
    "Language & Literature": ["language"],
    "Biography & Autobiography": ["Biography Novels"],
    "History & Politics": ["history"],
    "Philosophy & Religion": ["philosophy", "religion"],
    "Social Sciences": ["psychology"],
    "Lifestyle & Self-Help": ["self-help"],
    "Library & Reference": ["library"],
    "Other": [],
}

# ==== Synonyms → (category, topic_tags) ====
SYNONYMS = {

    "romantic": ("Novels", ["Romance Novels"]),
    "romance": ("Novels", ["Romance Novels"]),
    "love story": ("Novels", ["Romance Novels"]),

    "thriller": ("Novels", ["Thriller Novels"]),
    "horror": ("Novels", ["Horror Novels"]),
    "scifi": ("Novels", ["Science Fiction Novels"]),
    "sci fi": ("Novels", ["Science Fiction Novels"]),
    "sci-fi": ("Novels", ["Science Fiction Novels"]),
    "science fiction": ("Novels", ["Science Fiction Novels"]),

    "adventure": ("Novels", ["Action and Adventure Novels"]),
    "action": ("Novels", ["Action and Adventure Novels"]),
    "mystery": ("Novels", ["Mystery Novels"]),
    "detective": ("Novels", ["Mystery Novels"]),

    "fantasy": ("Novels", ["Fantasy Novels"]),
    "biography": ("Novels", ["Biography Novels"]),
    "biographies": ("Novels", ["Biography Novels"]),
    "business": ("Business", ["business"]),
    "health": ("Health & Medical", ["health"]),
    "data intro": ("Science", ["Data_Intro"]),
    "data advanced": ("Science", ["Data_Advanced"]),
    "education": ("Education", ["education"]),
    "language": ("Language & Literature", ["language"]),
    "history": ("History & Politics", ["history"]),
    "philosophy": ("Philosophy & Religion", ["philosophy"]),
    "religion": ("Philosophy & Religion", ["religion"]),
    "psychology": ("Social Sciences", ["psychology"]),
    "self-help": ("Lifestyle & Self-Help", ["self-help"]),
    "library": ("Library & Reference", ["library"]),
    "artificial intelligence": ("Technology", ["AI_Basics", "AI_Advanced"]),
    "ai": ("Technology", ["AI_Basics", "AI_Advanced"]),
    "data analysis": ("Science", ["Data_Advanced", "Data_Intro"]),
    "web development": ("Technology", ["FullStack_Frontend", "FullStack_Backend"]),
    "full stack": ("Technology", ["FullStack_Backend", "FullStack_Frontend"]),
    "frontend": ("Technology", ["FullStack_Frontend"]),
    "backend": ("Technology", ["FullStack_Backend"]),
    "web design": ("Arts & Design", ["WebDesign_UI", "WebDesign_UX"]),
    "ui design": ("Arts & Design", ["WebDesign_UI"]),
    "ux design": ("Arts & Design", ["WebDesign_UX"]),
}

GENRE_KEYWORDS = [
    "thriller", "horror", "romance", "sci-fi", "science fiction",
    "action", "adventure", "mystery", "fantasy", "biography",
    "ai", "artificial intelligence", "data",
]

FEELING_TOPIC_MAP = [
    # (keywords, category, [topics])
    (["sad", "depressed", "unhappy", "down", "blue"], "Lifestyle & Self-Help", ["self-help", "psychology"]),
    (["anxious", "worried", "stressed"], "Lifestyle & Self-Help", ["self-help", "psychology"]),
    (["lonely", "alone"], "Lifestyle & Self-Help", ["self-help"]),
    (["happy", "joyful", "excited"], "Novels", ["Romance Novels"]),
    (["motivated", "inspired"], "Business", ["business"]),
    (["lost", "confused", "searching"], "Philosophy & Religion", ["philosophy", "religion"]),
    (["curious", "interested"], "Science", ["Data_Intro", "Data_Advanced"]),
    (["bored"], "Novels", []),  # Any novel/fiction
    (["in love"], "Novels", ["Romance Novels"]),
    (["scared", "afraid"], "Novels", ["Horror Novels", "Thriller Novels"]),
]

# === Utility Functions ===
# Helper to detect if the user is asking about available book topics/categories
def detect_topic_or_category_question(msg: str) -> str | None:
    """
    Detects if the user is asking about topics or categories.
    Returns "topics" if asking about topics, "categories" if asking about categories, or None.
    """
    msg = msg.strip().lower().rstrip('?.!')
    # Topics
    if any(word in msg for word in ["topic", "topics"]):
        return "topics"
    # Categories
    if any(word in msg for word in ["category", "categories"]):
        return "categories"
    if any(word in msg for word in ["genre", "genres", "type", "types", "kind", "kinds"]):
        return "topics"
    return None

def get_order_related_response(msg, user, request):
    msg = msg.strip().lower().rstrip('?.!')

    # Payment method question: check for "pay", "payment", "checkout", "stripe"
    if any(word in msg for word in [
        "how can i pay", "payment method", "payment methods", "how does payment work", "how do i pay",
        "payment process", "checkout", "how can i checkout", "how do i complete my purchase", "stripe"
    ]):
        return (
            "You can pay securely using Stripe. All major credit and debit cards are supported.",
            [],
        )

    # Order history question
    if any(word in msg for word in [
        "show my orders", "show me my orders", "find my orders", "order history", "view orders", "see my orders"
    ]):
        link = request.build_absolute_uri(reverse("orders:order_history"))
        if user and user.is_authenticated:
            return (
                f"You can view all your orders here: <a href='{link}' target='_blank'>My Orders</a>",
                [],
            )
        else:
            return (
                "You need to log in to view your orders. Please log in first.",
                [],
            )

    # Return history question
    if any(word in msg for word in [
        "show my returns", "show me my returns", "find my returns", "return history", "view returns", "see my returns"
    ]):
        link = request.build_absolute_uri(reverse("orders:return_history"))
        if user and user.is_authenticated:
            return (
                f"You can view all your return requests here: <a href='{link}' target='_blank'>My Returns</a>",
                [],
            )
        else:
            return (
                "You need to log in to view your return requests. Please log in first.",
                [],
            )

    # Return policy period
    if any(word in msg for word in [
        "allowed return period", "how long can i return", "how many days", "return policy", "return period",
        "how long is the return period", "how long is return allowed"
    ]):
        return (
            "You can return your order within 14 days from the order creation date. Please check our return policy for details.",
            [],
        )

    # How to request a return
    if any(word in msg for word in [
        "how can i request a return", "how do i return an item", "how do i request a return",
        "send a return request", "make a return", "return an order", "request a return"
    ]):
        link = request.build_absolute_uri(reverse("orders:order_history"))
        if user and user.is_authenticated:
            return (
                f"To request a return, go to <a href='{link}' target='_blank'>My Orders</a> and click 'Request Return' next to the order you wish to return.",
                [],
            )
        else:
            return (
                "Please log in to request a return. Once logged in, go to 'My Orders' and select the order to request a return.",
                [],
            )

    # No order-related question matched
    return (None, [])

def detect_intent(user_message: str) -> str:
    """
    Intent detection:
    - Always returns BOOK_SEARCH if any book/tech/topic keyword is present in the message.
    - Prevents misclassifying short queries.
    """
    message = user_message.lower()
    tokens = set(re.split(r'\W+', message))

    book_words = {"book", "books", "novel", "story", "stories", "read", "reading", "author"}
    tech_words = set([
        "python", "java", "javascript", "react", "spring", "typescript", "nodejs", "angular", "vue",
        "ai", "machine", "learning", "web", "design", "development", "data", "analysis"
    ])
    if book_words & tokens or tech_words & tokens or message.strip() in tech_words:
        return "BOOK_SEARCH"
    if len(user_message.split()) <= 3 and not any(x in message for x in ["what", "who", "how", "where", "when", "why", "weather"]):
        return "BOOK_SEARCH"

    # Fallback to LLM if ambiguous
    prompt = (
        "You are an intent classifier for a digital bookshop chatbot. "
        "Classify the following user message into one of ONLY these categories:\n"
        "- BOOK_SEARCH: The user wants a book, book info, or recommendation.\n"
        "- BOOK_SENTIMENT: The user shares a feeling, opinion, praise, or complaint about the bookshop or books (even without asking a question).\n"
        "- OUT_OF_SCOPE: The user is not talking about books, bookstore, or reading at all.\n"
        "\n"
        "Return ONLY one of: BOOK_SEARCH, BOOK_SENTIMENT, OUT_OF_SCOPE.\n"
        "User: " + user_message.strip()
    )
    messages = [{"role": "system", "content": prompt}]
    intent, meta = ai_provider.get_chat_response(messages)
    if meta and meta.get("unavailable"):
        return "BOOK_SEARCH"
    return intent.strip().upper()

def _fallback_sentiment(text: str) -> str:
    """Use the existing mood vocabulary when provider classification is unavailable."""
    if re.search(r"\b(sad|depressed|unhappy|down|blue|anxious|worried|stressed|lonely|alone|lost|confused|scared|afraid)\b", text, re.I):
        return "Negative"
    if re.search(r"\b(happy|joyful|excited|motivated|inspired|curious|interested)\b|\bin love\b", text, re.I):
        return "Positive"
    return "Neutral"


def analyze_sentiment(text: str) -> str:
    """
    Preserve valid provider classifications; unavailable responses are not Neutral votes.
    """
    prompt = f"Analyze sentiment (Positive, Negative, or Neutral) of:\n{text}"
    messages = [
        {"role": "system", "content": "Only answer: Positive, Negative, or Neutral."},
        {"role": "user", "content": prompt},
    ]
    try:
        sentiment, meta = ai_provider.get_chat_response(messages)
        if meta and meta.get("unavailable"):
            return _fallback_sentiment(text)
        sentiment = sentiment.strip().capitalize()
        return sentiment if sentiment in ["Positive", "Negative", "Neutral"] else _fallback_sentiment(text)
    except Exception:
        return _fallback_sentiment(text)

def detect_feeling_and_category(msg):
    msg = msg.lower()
    for keywords, cat, topics in FEELING_TOPIC_MAP:
        for k in keywords:
            if k in msg:
                return cat, topics
    return None, []

def extract_interest(query: str) -> str:
    """
    Extracts the main interest or author from the user query.
    - If 'by', 'author', or 'authors' is present, returns the name(s) after it (for author search).
    - If 'about' is present, returns what's after it.
    - Else, tries to find the last tech/topic word in the query.
    - Fallback: returns the last word.
    """
    query = query.strip().lower()

    # 1. Check for 'by', 'author', or 'authors' (author search)
    m = re.search(r"(?:by|author|authors)\s+([a-zA-Z\s.&,-]+)", query)
    if m:
        # Clean up trailing "and"/"," if present (handles multiple authors simply)
        author_name = m.group(1).strip().strip(" ,.&")
        return author_name

    # 2. If 'about' exists, take what's after it
    parts = re.split(r"\babout\b", query, flags=re.IGNORECASE, maxsplit=1)
    if len(parts) > 1:
        return parts[1].strip()

    # 3. Try to get last tech/topic keyword
    words = query.split()
    tech_words = [
        "python", "java", "javascript", "react", "spring", "typescript", "nodejs", "angular", "vue",
        "ai", "machine", "learning", "web", "design", "development", "data", "analysis"
    ]
    for word in reversed(words):
        if word in tech_words:
            return word

    # 4. Fallback: return the last word
    return words[-1] if words else ""

def get_search_stopwords(categories, topics_by_category):
    """
    Generate a set of all stopwords including generic words, all categories, and all topics.
    """
    basic_stopwords = {
        "books", "book", "give", "show", "me", "some", "about", "find", "tell", "recommend",
        "please", "want", "need", "on", "for", "of", "the", "a", "an", "novels", "novel", "story", "stories",
        "read", "reading", "author", "authors", "by", "in",
        "and", "or", "is", "are", "was", "were", "it", "its", "this", "that", "these", "those",
        "what", "who", "how", "where", "when", "why",
        "can", "could", "should", "would", "do", "does",
        "if", "then", "else", "but", "so", "than", "searching ", "somthing "
    }
    cat_words = {cat.lower().replace("-", " ").replace("_", " ").strip() for cat in categories}
    topic_words = {
        topic.lower().replace("-", " ").replace("_", " ").strip()
        for topics in topics_by_category.values() for topic in topics
    }
    return basic_stopwords | cat_words | topic_words

def build_book_context(query=None, context_summary=None):
    """
    Returns a queryset of relevant books based on the user's query or session context.
    Only returns books for strict matches:
    1. Author search (if 'by' in query)
    2. Title search (excluding stopwords, categories, topics)
    3. Strict SYNONYMS (category + topic_tag) mapping (prefer longest/specific match)
    If no result, return None!
    """
    if not query and context_summary:
        query = context_summary
    if not query:
        return None

    # 1. Author search
    interest = extract_interest(query).lower().strip()
    if re.search(r"\bby\b", query.lower()):
        books = Book.objects.filter(authors__icontains=interest).order_by('?')
        if books.exists():
            return books

    # Prepare main words (excluding stopwords)
    stopwords = get_search_stopwords(CATEGORIES, topics_by_category)
    words = [w for w in re.split(r'\W+', interest) if w and w not in stopwords and len(w) > 2]

    # 2. Title search (use only these cleaned words)
    title_books = Book.objects.none()
    for w in words:
        qset = Book.objects.filter(title__istartswith=w).order_by('?')
        title_books = title_books | qset
    if not title_books.exists():
        for w in words:
            qset = Book.objects.filter(title__icontains=w).order_by('?')
            title_books = title_books | qset

    # 3. Strict SYNONYMS (category + topic_tag) mapping
    lower_query = query.lower()
    sorted_keys = sorted(SYNONYMS.keys(), key=lambda x: -len(x))
    found_synonym = None
    specific_topics = []
    for syn in sorted_keys:
        if syn in lower_query:
            found_synonym = syn
            break
    synonym_books = Book.objects.none()
    if found_synonym:
        cat, topics = SYNONYMS[found_synonym]
        specific_topics = topics
        topic_q = Q()
        for t in topics:
            topic_q |= Q(topic_tag__iexact=t) | Q(topic_tag__icontains=t)
        if topics:
            synonym_books = Book.objects.filter(Q(category__name__iexact=cat) & topic_q).order_by('?')
        else:
            synonym_books = Book.objects.filter(Q(category__name__iexact=cat)).order_by('?')

    # 4. Combine and filter
    combined_books = (title_books | synonym_books).distinct()

    if found_synonym and specific_topics and found_synonym not in {"novels", "novel", "story", "stories"}:
        combined_books = combined_books.filter(topic_tag__in=specific_topics)

    if combined_books.exists():
        return combined_books#

    return None

def detect_known_topic(msg: str, threshold: int = 70) -> str | None:
    """
    Detects known genre keywords in a user message, using exact and fuzzy matching.
    """
    if not msg:
        return None
    msg = msg.lower()
    words = msg.split()
    for word in words:
        for genre in GENRE_KEYWORDS:
            if word == genre or genre.startswith(word) or word.startswith(genre[:3]):
                return genre
    for word in words:
        match, score, _ = process.extractOne(word, GENRE_KEYWORDS)
        if score >= threshold:
            return match
    for genre in GENRE_KEYWORDS:
        if genre in msg:
            return genre
    return None

def apply_book_filters(books, price_filter=None, rating_filter=None, stock_status=None):
    """
    Apply optional filters to a queryset of books:
    - price_filter: dict like {"min": 10, "max": 30} or None
    - rating_filter: dict like {"min": 4.5} or None
    - stock_status: "In Stock" / "Limited Stock" or None
    """
    def to_float(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    # 1. Annotate ratings
    books = books.annotate(average_rating=Avg('reviews__rating'))

    # 2. Price filter
    if price_filter:
        min_p = to_float(price_filter.get("min"))
        max_p = to_float(price_filter.get("max"))
        if min_p is not None:
            books = books.filter(price__gte=min_p)
        if max_p is not None:
            books = books.filter(price__lte=max_p)

    # 3. Rating filter
    if rating_filter:
        min_r = to_float(rating_filter.get("min"))
        if min_r is not None:
            books = books.filter(average_rating__gte=min_r)

    # 4. Stock filter
    if stock_status in ("In Stock", "Limited Stock"):
        books = books.filter(stock_status=stock_status)

    return books

# === Main API Endpoints ===
def chatbot_api(request: HttpRequest):
    """
    Main POST endpoint for chatbot messages.
    Handles order/payment queries, quick reply for category, topic questions,
    interest, feelings, and book search & filtering.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        data = json.loads(request.body)
        user_msg = (data.get("message") or "").strip()
        price_filter = data.get("price_filter")
        rating_filter = data.get("rating_filter")
        stock_status_filter = data.get("stock_status")
    except Exception:
        return JsonResponse({"error": "Invalid JSON."}, status=400)
    if not user_msg:
        return JsonResponse({"error": "Empty message."}, status=400)

    if len(user_msg) > settings.CHAT_MAX_MESSAGE_LENGTH:
        return JsonResponse({"error": "Message is too long."}, status=400)
    for value, allowed in ((price_filter, {"min", "max"}), (rating_filter, {"min"})):
        if value is not None:
            if not isinstance(value, dict) or set(value) - allowed:
                return JsonResponse({"error": "Invalid filters."}, status=400)
            for number in value.values():
                try:
                    valid = not isinstance(number, bool) and math.isfinite(float(number)) and float(number) >= 0
                except (ValueError, TypeError, OverflowError):
                    valid = False
                if not valid:
                    return JsonResponse({"error": "Invalid filter value."}, status=400)
    if stock_status_filter not in (None, "", "In Stock", "Limited Stock"):
        return JsonResponse({"error": "Invalid stock filter."}, status=400)
    if not request.session.session_key:
        request.session.create()
    rate_key = "chat-rate:" + request.session.session_key
    cache.add(rate_key, 0, 60)
    try:
        count = cache.incr(rate_key)
    except ValueError:
        cache.set(rate_key, 1, 60)
        count = 1
    if count > settings.CHAT_REQUESTS_PER_MINUTE:
        return JsonResponse({"error": "Please wait before sending more messages."}, status=429)

    # Identify user and session
    user = request.user if request.user.is_authenticated else None
    session = get_or_create_session(user, request)
    summary = getattr(session.conversationcontext, "summary", "") if hasattr(session, "conversationcontext") else ""

    # Store the user message in chat history
    ChatMessage.objects.create(session=session, role="user", content=user_msg)

    # 1) Handle order/payment/returns questions (early exit if handled)
    order_reply, order_quick = get_order_related_response(user_msg, user, request)
    if order_reply:
        ChatMessage.objects.create(
            session=session,
            role="assistant",
            content=order_reply,
            suggested_books=[],
            sentiment="Neutral",
        )
        return JsonResponse({
            "reply": order_reply,
            "session_id": str(session.session_id),
            "quick_replies": order_quick,
            "sentiment": "Neutral",
            "books": [],
        })

    # 2) Handle quick reply for CATEGORY name (this must come BEFORE topic questions!)
    if user_msg in CATEGORIES:
        # Fetch books by category name
        books = Book.objects.filter(category__name__iexact=user_msg).order_by('?')
        if books.exists():
            books = books.annotate(average_rating=Avg('reviews__rating'), num_reviews=Count('reviews'))
            books = apply_book_filters(books, price_filter, rating_filter, stock_status_filter)[:MAX_BOOKS]
            custom_intro = f"Here are some books from {user_msg}:"
            book_list = []
            for b in books:
                book_list.append({
                    "title": b.title,
                    "authors": b.authors,
                    "description": (b.description or "")[:160],
                    "category": b.category.name if getattr(b, "category", None) else "",
                    "topic_tag": getattr(b, "topic_tag", "") or "",
                    "price": str(b.price),
                    "link": request.build_absolute_uri(reverse("books:book_detail", args=[b.slug])),
                    "cover_url": b.thumbnail or "/static/images/placeholder.jpg",
                    "stock_status": getattr(b, "stock_status", "Available"),
                    "average_rating": round(b.average_rating, 1) if getattr(b, 'average_rating', None) else None,
                    "num_reviews": getattr(b, 'num_reviews', 0),
                    "slug": b.slug,
                })
            # Store assistant reply in chat history
            ChatMessage.objects.create(
                session=session,
                role="assistant",
                content=custom_intro,
                suggested_books=book_list,
                sentiment="Neutral",
            )
            if session.user:
                summarize_session(session)
            return JsonResponse({
                "reply": custom_intro,
                "session_id": str(session.session_id),
                "quick_replies": [],
                "sentiment": "Neutral",
                "books": book_list,
            })
        else:
            # No books in this category
            reply = (
                f"Sorry, there are currently no books available in {user_msg}. "
                f"Would you like to explore another category?"
            )
            ChatMessage.objects.create(
                session=session,
                role="assistant",
                content=reply,
                suggested_books=[],
                sentiment="Neutral",
            )
            quick = [c for c in CATEGORIES if c != user_msg]
            return JsonResponse({
                "reply": reply,
                "session_id": str(session.session_id),
                "quick_replies": quick,
                "sentiment": "Neutral",
                "books": [],
            })

    # 3) Handle topic/category questions like "what topics do you have?" or "what categories do you have?"
    what = detect_topic_or_category_question(user_msg)
    if what == "topics":
        # 1. Gather all topics in original order
        all_topics = [t for tlist in topics_by_category.values() for t in tlist]
        seen = set()
        unique_topics = [t for t in all_topics if not (t in seen or seen.add(t))]

        # 2. Find all topic_tag values from previous assistant replies in this session
        asked = []
        assistant_msgs = session.chatmessage_set.filter(role="assistant") \
                        .values_list("suggested_books", flat=True)
        for suggested in assistant_msgs:
            for book in (suggested or []):
                tag = book.get("topic_tag")
                if tag and tag not in asked:
                    asked.append(tag)

        # 3. Put topics already suggested first, rest after
        ordered = [t for t in unique_topics if t in asked] + \
                [t for t in unique_topics if t not in asked]

        reply = "Here are the topics you've shown interest in, followed by the rest:"
        ChatMessage.objects.create(
            session=session,
            role="assistant",
            content=reply,
            suggested_books=[],
            sentiment="Neutral",
        )
        return JsonResponse({
            "reply": reply,
            "session_id": str(session.session_id),
            "quick_replies": ordered,
            "sentiment": "Neutral",
            "books": [],
        })


    elif what == "categories":
        # 1. Get all categories in their default order
        categories_all = CATEGORIES[:]

        # 2. Collect all categories that have already been suggested in previous assistant replies for this session
        used_cats = []
        assistant_msgs = session.chatmessage_set.filter(role="assistant") \
                        .values_list("suggested_books", flat=True)
        for suggested in assistant_msgs:
            for book in (suggested or []):  # suggested can be None!
                cat = book.get("category")
                if cat and cat not in used_cats:
                    used_cats.append(cat)

        # 3. Build the final order: used categories first, then the remaining ones
        ordered_cats = [c for c in categories_all if c in used_cats] + \
                    [c for c in categories_all if c not in used_cats]

        reply = "Here are the categories you've already explored, followed by the rest:"
        ChatMessage.objects.create(
            session=session,
            role="assistant",
            content=reply,
            suggested_books=[],
            sentiment="Neutral",
        )
        return JsonResponse({
            "reply": reply,
            "session_id": str(session.session_id),
            "quick_replies": ordered_cats,
            "sentiment": "Neutral",
            "books": [],
        })

    # 4) Handle intent, interest, feeling, or regular book search
    interest_cat = None
    interest_topics = []
    raw_interest = ""
    if re.search(r"\b(curious about|interested in)\b", user_msg, re.IGNORECASE):
        raw_interest = extract_interest(user_msg)
        # Map interest keywords to category/topics
        if "technology" in raw_interest.lower():
            interest_cat = "Technology"
            interest_topics = topics_by_category.get("Technology", [])
        elif raw_interest.lower().strip() in SYNONYMS:
            interest_cat, interest_topics = SYNONYMS[raw_interest.lower().strip()]

    # Detect feelings (sad, motivated, etc)
    feel_cat, feel_topics = detect_feeling_and_category(user_msg)

    # Priority: interest > feeling > normal search
    books = None
    custom_intro = None
    sentiment = analyze_sentiment(user_msg or summary)
    if interest_cat:
        q = Q(category__name__iexact=interest_cat)
        if interest_topics:
            topic_query = Q()
            for t in interest_topics:
                topic_query |= Q(topic_tag__icontains=t)
            q &= topic_query
        books = Book.objects.filter(q).order_by('?')
        if books.exists():
            books = books.annotate(average_rating=Avg('reviews__rating'), num_reviews=Count('reviews'))
            books = apply_book_filters(books, price_filter, rating_filter, stock_status_filter)[:MAX_BOOKS]
            custom_intro = (
                f"You mentioned you’re curious about “{raw_interest}”. "
                f"Here are some titles in {interest_cat}:"
            )

    elif feel_cat:
        felt_keyword = next((k for kws, _, _ in FEELING_TOPIC_MAP for k in kws if k in user_msg.lower()), feel_cat)
        empathy_prefix = (
            f"I'm sorry to hear you're feeling {felt_keyword}. " if sentiment == "Negative"
            else ("Thanks for sharing! " if sentiment == "Positive" else "Thanks for sharing. ")
        )
        q = Q(category__name__iexact=feel_cat)
        if feel_topics:
            topic_query = Q()
            for t in feel_topics:
                topic_query |= Q(topic_tag__icontains=t)
            q &= topic_query
        books = Book.objects.filter(q).order_by('?')
        if books.exists():
            books = books.annotate(average_rating=Avg('reviews__rating'), num_reviews=Count('reviews'))
            books = apply_book_filters(books, price_filter, rating_filter, stock_status_filter)[:MAX_BOOKS]
            custom_intro = (
                f"{empathy_prefix}Here are some {feel_cat} books that might help:"
            )

    else:
        # Handle general intent (search, sentiment, etc.)
        intent = detect_intent(user_msg)
        if intent == "BOOK_SEARCH":
            result_qs = build_book_context(query=user_msg, context_summary=summary)
            if result_qs and result_qs.exists():
                books = result_qs.annotate(average_rating=Avg('reviews__rating'), num_reviews=Count('reviews'))
                books = apply_book_filters(books, price_filter, rating_filter, stock_status_filter)[:MAX_BOOKS]
                custom_intro = "Here are some books you may like:"
            else:
                custom_intro = None
        elif intent == "BOOK_SENTIMENT":
            if sentiment == "Positive":
                custom_intro = "Thank you for your kind words! 😊 We're glad you enjoy our bookstore.<br>Discover more of what we offer below!"
            elif sentiment == "Negative":
                custom_intro = "Sorry to hear that. We’ll do our best to improve! 🙁<br>In the meantime, you can explore more categories:"
            else:
                custom_intro = "Thank you for your feedback! 😐<br>Feel free to explore more books and categories:"

        elif intent == "OUT_OF_SCOPE":
            custom_intro = (
                "📚 I'm a digital assistant specialized in books and personalized recommendations.\n"
                "❓ I’m not able to answer questions outside the bookstore context.\n"
                "👉 Feel free to ask me anything about books, reading, authors, or our shop — I’d be happy to help! 😊"
            )
    # Prepare response
    quick = []
    book_list = []
    if books and books.exists():
        reply = custom_intro or "Here are some books you may like:"
        for b in books:
            book_list.append({
                "title": b.title,
                "authors": b.authors,
                "description": (b.description or "")[:160],
                "category": b.category.name if getattr(b, "category", None) else "",
                "topic_tag": getattr(b, "topic_tag", "") or "",
                "price": str(b.price),
                "link": request.build_absolute_uri(reverse("books:book_detail", args=[b.slug])),
                "cover_url": b.thumbnail or "/static/images/placeholder.jpg",
                "stock_status": getattr(b, "stock_status", "Available"),
                "average_rating": round(b.average_rating, 1) if getattr(b, 'average_rating', None) else None,
                "num_reviews": getattr(b, 'num_reviews', 0),
                "slug": b.slug,
            })
    else:
        reply = custom_intro or (
            "Sorry, I couldn't find any books matching your request. "
            "Would you like to explore one of these categories?"
        )
        quick = list(Book.objects.values_list("category__name", flat=True).distinct())
        book_list = []

    # Store assistant message in chat history
    ChatMessage.objects.create(
        session=session,
        role="assistant",
        content=reply,
        suggested_books=book_list,
        sentiment=sentiment,
    )

    # Optionally update session summary
    if session.user:
        summarize_session(session)

    # Final response
    return JsonResponse({
        "reply": reply,
        "session_id": str(session.session_id),
        "quick_replies": quick,
        "sentiment": sentiment,
        "books": book_list,
    })

def _history_messages(session):
    messages = list(session.chatmessage_set.order_by("timestamp").values(
        "role", "content", "suggested_books", "sentiment"
    ))
    # Old sessions stored a generated welcome as well as returning a welcome banner.
    # Hide only those leading generated greetings; retain every conversation reply.
    while messages:
        first = messages[0]
        content = first["content"]
        if (first["role"] != "assistant" or first["suggested_books"]
                or not content.startswith(("Good morning!", "Good afternoon!", "Good evening!"))
                or not all(phrase in content for phrase in (
                    "Show me some sci-fi novels", "Recommend books to learn Python",
                    "Give me a romantic story", "What are you in the mood for today?"))):
            break
        messages.pop(0)
    return messages


@ensure_csrf_cookie
@require_GET
def chat_history(request):
    sid = request.GET.get("session_id")
    if sid:
        try:
            owned = ChatSession.objects.filter(user=request.user) if request.user.is_authenticated else ChatSession.objects.filter(user=None, visitor_id=request.session.get("visitor_id") or "")
            session = owned.get(session_id=uuid.UUID(sid))
        except (ChatSession.DoesNotExist, ValueError, ValidationError):
            return JsonResponse({"error": "Session not found"}, status=404)
        msgs = _history_messages(session)
        if session.user:
            welcome = get_dynamic_welcome(session.user.username)
        else:
            welcome = get_dynamic_welcome()
        return JsonResponse({
            "messages": list(msgs),
            "session_id": str(session.session_id),
            "welcome_message": welcome,
        })

    # If no session_id, return all messages for the current user or guest
    user = request.user if request.user.is_authenticated else None
    if user:
        sessions = ChatSession.objects.filter(user=user).order_by("-created_at")[:10]
        if not sessions.exists():
            # Create a new session for this user
            session = get_or_create_session(user, request)
            sessions = ChatSession.objects.filter(user=user).order_by("-created_at")[:10]

        all_sessions = []
        for session in sessions:
            msgs = _history_messages(session)
            all_sessions.append({
                "session_id": str(session.session_id),
                "created_at": session.created_at.strftime("%Y-%m-%d %H:%M"),
                "messages": list(msgs)
            })
        welcome = get_dynamic_welcome(user.username)
        return JsonResponse({
            "all_sessions": all_sessions,
            "welcome_message": welcome,
        })

    else:
        # Visitor: one session only
        session = get_or_create_session(None, request)
        msgs = _history_messages(session)
        welcome = get_dynamic_welcome()
        return JsonResponse({
            "messages": list(msgs),
            "session_id": str(session.session_id),
            "welcome_message": welcome,
        })
