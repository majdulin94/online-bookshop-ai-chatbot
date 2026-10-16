import uuid
from django.utils.crypto import get_random_string
from django.conf import settings
from django.utils import timezone
from chatbot.models import ChatSession, ConversationContext
from chatbot.config import OPENAI_MODEL, SESSION_DURATION
from chatbot.ai_providers.gpt_provider import GPTProvider


def get_or_create_session(user=None, request=None):
    # Case for guest user (not logged in)
    if not user or not user.is_authenticated:
        if request:
            visitor_id = request.session.get("visitor_id")
            if not visitor_id:
                visitor_id = get_random_string(32)
                request.session["visitor_id"] = visitor_id

            # Now we search by visitor_id (not session_id)
            latest = ChatSession.objects.filter(user=None, status="active", visitor_id=visitor_id).first()
            if latest and not latest.is_expired():
                return latest

            if latest:
                latest.mark_expired()
                summary = getattr(getattr(latest, "conversationcontext", None), "summary", "")
            else:
                summary = ""

            session = ChatSession.objects.create(
                user=None,
                visitor_id=visitor_id,
                expires_at=timezone.now() + SESSION_DURATION,
                status="active"
            )
            ConversationContext.objects.create(session=session, summary=summary)

            return session
        else:
            raise Exception("Visitor session requires `request` object.")

    # Case for logged-in user
    latest = (
        ChatSession.objects.filter(user=user, status="active")
        .order_by("-created_at")
        .first()
    )

    if latest and not latest.is_expired():
        latest.extend_if_logged_in()
        return latest

    if latest:
        latest.mark_expired()
        summary = getattr(getattr(latest, "conversationcontext", None), "summary", "")
    else:
        summary = ""

    session = ChatSession.objects.create(
        user=user,
        expires_at=timezone.now() + SESSION_DURATION,
        status="active"
    )
    ConversationContext.objects.create(session=session, summary=summary)

    return session

ai_provider = GPTProvider(api_key=settings.OPENAI_API_KEY, model=OPENAI_MODEL)


def summarize_session(session):
    if not session.user:
        return "" # No summary for guest users
    # Aktuelle User-Messages abrufen
    user_messages = session.chatmessage_set.filter(role="user").order_by("timestamp")
    new_texts = [m.content.strip() for m in user_messages if m.content.strip()]
    new_input = "\n".join(new_texts)[-12000:]

    # Alte Zusammenfassung der letzten Session
    try:
        previous_session = (
            ChatSession.objects.filter(user=session.user, status="expired")
            .exclude(id=session.id)
            .order_by("-created_at")
            .first()
        )
        old_summary = previous_session.conversationcontext.summary.strip()
    except Exception:
        old_summary = ""

    # Prompt vorbereiten
    system_prompt = (
        "You are an assistant summarizing a user's book preferences and intentions over time. "
        "Given a previous summary and new user inputs, create a new, concise summary that reflects all important information. "
        "Be specific (e.g., genre preferences, intent to get future recommendations)."
    )

    prompt = (
        f"Previous Summary:\n{old_summary}\n\n"
        f"New User Messages:\n{new_input}"
    )


    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    # KI aufrufen
    try:
        updated_summary, meta = ai_provider.get_chat_response(messages)
        if meta and meta.get("unavailable"):
            return getattr(getattr(session, "conversationcontext", None), "summary", "")

        # Speichern in ConversationContext
        context, _ = ConversationContext.objects.get_or_create(session=session)
        context.summary = updated_summary
        context.summary_updated_at = timezone.now()  # Update timestamp
        context.save()

        return updated_summary

    except Exception:
        # Keep existing preferences when an external service is unavailable.
        return getattr(getattr(session, "conversationcontext", None), "summary", "")
