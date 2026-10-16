import openai
import logging
from .base import AIProvider
from django.conf import settings

class GPTProvider(AIProvider):
    def __init__(self, api_key=None, model=None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL

    def get_chat_response(self, messages: list) -> tuple:
        if not settings.EXTERNAL_SERVICES_ENABLED or not self.api_key:
            return "Neutral", {"unavailable": True}
        try:
            client = openai.OpenAI(api_key=self.api_key, timeout=15, max_retries=0)
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=500,
            )
            ai_text = response.choices[0].message.content.strip()
            return ai_text, None
        except (openai.OpenAIError, ValueError, AttributeError):
            logging.getLogger(__name__).warning("OpenAI response unavailable")
            return "Neutral", {"unavailable": True}
