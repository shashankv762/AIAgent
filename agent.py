"""
agent.py — Core AI Agent

Loads API keys from the .env file (never hardcoded).
Uses the Groq API for fast LLM inference and optionally logs
interactions to Hindsight for evaluation and feedback.
"""

import os
import requests
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env (silently ignored if not present)
load_dotenv()

# ── API clients ────────────────────────────────────────────────────────────────

def _get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY is not set. "
            "Copy .env.example to .env and fill in your key."
        )
    return Groq(api_key=api_key)


def _get_hindsight_key() -> str | None:
    """Return the Hindsight API key, or None if not configured."""
    return os.getenv("HINDSIGHT_API_KEY")


# ── Hindsight logging ──────────────────────────────────────────────────────────

HINDSIGHT_LOG_URL = "https://api.hindsight.so/v1/log"


def _log_to_hindsight(prompt: str, response: str) -> None:
    """Send a prompt/response pair to Hindsight for evaluation (best-effort)."""
    key = _get_hindsight_key()
    if not key:
        return
    try:
        requests.post(
            HINDSIGHT_LOG_URL,
            json={"prompt": prompt, "response": response},
            headers={"Authorization": f"Bearer {key}"},
            timeout=5,
        )
    except requests.RequestException:
        # Logging is non-critical; never crash the agent because of it
        pass


# ── Agent ──────────────────────────────────────────────────────────────────────

DEFAULT_MODEL = "llama3-8b-8192"
DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful AI assistant. "
    "Answer questions clearly and concisely."
)


class AIAgent:
    """A simple conversational AI agent backed by the Groq LLM API."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        self.model = model
        self.system_prompt = system_prompt
        self.client = _get_groq_client()
        self.history: list[dict] = []

    # ── Public API ─────────────────────────────────────────────────────────────

    def chat(self, user_message: str) -> str:
        """Send a message and return the assistant's reply."""
        self.history.append({"role": "user", "content": user_message})

        messages = [{"role": "system", "content": self.system_prompt}] + self.history

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )

        reply = completion.choices[0].message.content or ""
        self.history.append({"role": "assistant", "content": reply})

        _log_to_hindsight(user_message, reply)

        return reply

    def reset(self) -> None:
        """Clear the conversation history."""
        self.history = []
