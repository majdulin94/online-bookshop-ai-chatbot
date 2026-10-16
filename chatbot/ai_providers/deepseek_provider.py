from .base import AIProvider

class DeepSeekProvider(AIProvider):
    """
    Mock DeepSeek Provider for demonstration.
    This does not call any real API, just returns a fixed/fake response.
    """
    def __init__(self, api_key=None, model=None):
        self.api_key = api_key
        self.model = model

    def get_chat_response(self, messages: list) -> tuple:
        # Extract the content of the last message, just for demonstration
        user_text = ""
        for msg in messages[::-1]:
            if msg["role"] == "user":
                user_text = msg["content"]
                break
        # For demonstration only, the response depends on the user's text
        if "thriller" in user_text.lower():
            return "Here are some DeepSeek thriller books!", None
        elif "hello" in user_text.lower():
            return "DeepSeek says: Hello!", None
        else:
            return "This is a mock DeepSeek response.", None
