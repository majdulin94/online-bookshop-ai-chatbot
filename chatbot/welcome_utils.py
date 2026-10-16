import datetime
import random
import time
random.seed(time.time())

# Basic greetings based on the current time
def get_time_based_greeting(username=None):
    hour = datetime.datetime.now().hour
    if hour < 12:
        return "Good morning! ☀️ Ready to discover your next favorite book?"
    elif hour < 18:
        return "Good afternoon! 📚 Looking for book recommendations?"
    else:
        return "Good evening! 🌙 What would you like to read tonight?"

# Example prompts
EXAMPLES = [
    '• “Show me some sci-fi novels”',
    '• “Recommend books to learn Python”',
    '• “Give me a romantic story”'
]
def get_examples_text():
    return "For example, try asking:\n" + "\n".join(EXAMPLES)

# Highlight AI features
AI_FEATURES = "🤖 I’m an AI-assisted assistant. Ask me for recommendations by mood, price, or availability."

# Extra random welcome messages (optional)
WELCOME_MESSAGES = [
    "Hi! 👋 What would you like to read today?",
    "Welcome back! 📚 Let’s find you a great book.",
    "Need a book suggestion? I’m here to help!",
    "Hello! Ask me for book recommendations, any genre!",
]
def get_random_welcome():
    return random.choice(WELCOME_MESSAGES)

# Final function that combines everything
def get_dynamic_welcome(username=None):
    parts = [
        get_time_based_greeting() + " " + get_random_welcome(),
        "",
        AI_FEATURES,
        get_examples_text(),
        "",
        "What are you in the mood for today? 😊",
    ]
    return "\n".join(parts)