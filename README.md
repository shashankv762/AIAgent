# AIAgent

A conversational AI agent powered by the [Groq](https://groq.com/) LLM API with optional interaction logging via [Hindsight](https://hindsight.so/).

## Project structure

```
AIAgent/
├── agent.py          # Core agent — Groq client + Hindsight logging
├── main.py           # Interactive CLI entry point
├── requirements.txt  # Python dependencies
├── .env.example      # Template — copy to .env and fill in your keys
├── .gitignore        # Excludes .env and other non-source files
└── README.md
```

## Environment setup

API keys are **never** hardcoded in source files. They are loaded from a `.env` file that is excluded from version control via `.gitignore`.

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Open `.env` and fill in your real keys:
   ```
   GROQ_API_KEY=your_groq_api_key_here
   HINDSIGHT_API_KEY=your_hindsight_api_key_here
   ```

   > `HINDSIGHT_API_KEY` is optional. If omitted, interaction logging is simply skipped.

3. **Never commit `.env` to Git.** It is already listed in `.gitignore`.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running the agent

```bash
python main.py
```

You will see an interactive prompt:

```
╔══════════════════════════════════════╗
║          AIAgent  — powered by Groq  ║
╚══════════════════════════════════════╝
Commands: 'reset' = new conversation  |  'quit' / 'exit' = stop

You: Hello!

Agent: Hi there! How can I help you today?

You:
```

| Command | Effect |
|---------|--------|
| `reset` | Clears the conversation history and starts fresh |
| `quit` / `exit` | Stops the agent |

## How it works

- `agent.py` reads `GROQ_API_KEY` from the environment (via `python-dotenv`) and creates a `Groq` client.
- Each call to `AIAgent.chat()` appends the user message to the conversation history, sends the full context to the Groq API, records the reply, and optionally posts the pair to the Hindsight logging endpoint.
- The `main.py` CLI wraps `AIAgent` in a simple read-eval-print loop.