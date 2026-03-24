# 🧑‍💻 AI Coding Practice Mentor

> A personalised AI coding tutor that **remembers every student's mistakes, languages, and behaviour patterns across all sessions** — powered by Groq LLM and Hindsight Cloud persistent memory.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Streamlit UI                      │
│  Tab 1: Debug  │  Tab 2: Challenge  │  Tab 3: Path  │
│                      Tab 4: Memory                   │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │   CodingMentorAgent    │  ◄── agent.py
            │   (OpenClaw-style loop)│
            └───────┬────────┬───────┘
                    │        │
          ┌─────────▼──┐  ┌──▼──────────────┐
          │  Groq LLM  │  │ MemoryManager   │  ◄── memory_manager.py
          │(llama-3.3) │  │                 │
          └────────────┘  │  Primary:       │
                          │  Hindsight Cloud│
                          │  (vector store) │
                          │                 │
                          │  Fallback:      │
                          │  memory_store   │
                          │  .json (local)  │
                          └─────────────────┘
```

---

## Setup

```bash
cd ai_coding_mentor
pip install -r requirements.txt
```

## Run

```bash
streamlit run ai_coding_mentor/app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

---

## File Structure

```
ai_coding_mentor/
├── app.py              Main Streamlit UI (4 tabs)
├── agent.py            CodingMentorAgent — OpenClaw-style reasoning loop
├── memory_manager.py   Hindsight Cloud API + local JSON fallback
├── prompts.py          All LLM system/user prompt templates
├── utils.py            Helpers: language detection, code extraction, JSON parsing
├── memory_store.json   Local fallback memory store (auto-created if missing)
├── requirements.txt    Python dependencies
└── README.md           This file
```

---

## How Memory Works

Hindsight Cloud is a **vector-backed persistent memory API**. The app uses it as follows:

| Action | Endpoint | When |
|--------|----------|------|
| **Write** a mistake/fix/behaviour | `POST /v1/memories` | After every debug session |
| **Query** relevant past mistakes | `POST /v1/memories/query` | Before building the debug prompt |
| **List all** memories | `GET /v1/memories?user_id=…` | Memory dashboard & Raw Memory tab |
| **Delete all** memories | `DELETE /v1/memories?user_id=…` | Reset Memory button |

### Local Fallback

Every `write_memory` call **also** mirror-writes to `memory_store.json`. If the Hindsight Cloud API is unreachable, all reads fall back to this local file with keyword-based search. Streamlit displays a yellow warning banner whenever the fallback is active.

---

## The OpenClaw Agent Loop

When a student submits broken code, the agent runs these 9 steps in order:

```
Step 1 → Read memory     Query Hindsight Cloud for this student's past mistakes
Step 2 → Build context   Format Hindsight results into a readable numbered list
Step 3 → Build prompt    Inject code + error + memory context into debug prompt
Step 4 → Call Groq       Send system + user prompt; temp=0.3, max_tokens=2048
Step 5 → Parse response  Extract fixed code block via regex r"```[\w]*\n(.*?)```"
Step 6 → Detect pattern  Run heuristic behaviour detection on the submitted code
Step 7 → Write memory    POST new mistake, fix, and behaviour note to Hindsight
Step 8 → Update counters Increment session_count and fixes_count (implicit in save)
Step 9 → Return result   Return dict { analysis, fixed_code, past_context, behavior }
```

---

## App Features

| Tab | Feature | Description |
|-----|---------|-------------|
| 🐛 | **Debug My Code** | Personalized debugger using your full mistake history as context |
| 🎯 | **Coding Challenge** | Adaptive challenges targeting your weakest areas |
| 🗺️ | **Learning Path** | 3 personalised next-step recommendations based on your history |
| 📜 | **Raw Memory** | Live view of all Hindsight Cloud entries; JSON export |

### Memory Dashboard (Sidebar)
- Language badges coloured green
- Last 3 mistakes as cards with red BUG badge
- Behaviour pattern bullets
- Session count and fixes count metrics
- Reset Memory button
- Hindsight Cloud connection status indicator

---

## API Keys

API keys are embedded directly in `agent.py` (`GROQ_API_KEY`) and `memory_manager.py`
(`HINDSIGHT_API_KEY`). For production use, move these to environment variables or a
`.env` file and load them with `python-dotenv`.

---

## Fallback Behaviour

When Hindsight Cloud is unreachable:

1. Every `write_memory` call still succeeds by writing to `memory_store.json`.
2. `query_memories` performs a simple keyword-match against the local JSON.
3. `list_all_memories` returns all entries from the local JSON.
4. `reset_memory` clears the local JSON entry even if the remote DELETE fails.
5. A yellow Streamlit warning is shown to the user for every fallback operation.