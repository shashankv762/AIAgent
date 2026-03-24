"""
main.py — Interactive CLI for AIAgent

Run:
    python main.py

Type 'reset' to clear the conversation history.
Type 'quit' or 'exit' to stop.
"""

import requests
from agent import AIAgent


def main() -> None:
    print("╔══════════════════════════════════════╗")
    print("║          AIAgent  — powered by Groq  ║")
    print("╚══════════════════════════════════════╝")
    print("Commands: 'reset' = new conversation  |  'quit' / 'exit' = stop\n")

    agent = AIAgent()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in {"quit", "exit"}:
            print("Goodbye!")
            break

        if user_input.lower() == "reset":
            agent.reset()
            print("[Conversation history cleared]\n")
            continue

        try:
            reply = agent.chat(user_input)
            print(f"\nAgent: {reply}\n")
        except EnvironmentError as exc:
            print(f"\n[Configuration error] {exc}\n")
            break
        except requests.RequestException as exc:
            print(f"\n[API request failed] {exc} — please try again.\n")
        except Exception as exc:  # noqa: BLE001
            print(f"\n[Unexpected error] {exc}\n")
            break


if __name__ == "__main__":
    main()
