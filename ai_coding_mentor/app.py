"""
app.py
======
Main Streamlit UI for the AI Coding Practice Mentor.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import json
import sys
import os

# Allow imports from the same directory regardless of working directory
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

from agent import CodingMentorAgent
from memory_manager import MemoryManager

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AI Coding Practice Mentor",
    page_icon="🧑‍💻",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — GitHub dark theme
# ---------------------------------------------------------------------------

st.markdown(
    """
<style>
/* ── Global ─────────────────────────────────────────────────────────────── */
html, body, [class*="css"] {
    background-color: #0d1117 !important;
    color: #c9d1d9 !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial,
                 sans-serif, "Apple Color Emoji", "Segoe UI Emoji" !important;
}

/* ── Cards ──────────────────────────────────────────────────────────────── */
.mentor-card {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
}

/* ── Badges ─────────────────────────────────────────────────────────────── */
.badge-mistake {
    display: inline-block;
    background-color: #3d1f1f;
    color: #f85149;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
    margin-right: 6px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.badge-language {
    display: inline-block;
    background-color: #1f3d2e;
    color: #3fb950;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
    margin-right: 4px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.badge-resource {
    display: inline-block;
    background-color: #1f2d3d;
    color: #58a6ff;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
}

/* ── Buttons ────────────────────────────────────────────────────────────── */
div.stButton > button {
    background-color: #1f6feb !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    padding: 8px 20px !important;
}
div.stButton > button:hover {
    background-color: #388bfd !important;
}

/* ── Text areas / inputs ────────────────────────────────────────────────── */
textarea, input[type="text"] {
    background-color: #0d1117 !important;
    color: #c9d1d9 !important;
    border: 1px solid #30363d !important;
    border-radius: 6px !important;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace !important;
}

/* ── Code blocks ────────────────────────────────────────────────────────── */
code, pre {
    background-color: #0d1117 !important;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace !important;
}

/* ── Challenge box ──────────────────────────────────────────────────────── */
.challenge-box {
    background-color: #0d1b2e;
    border: 1px solid #1f6feb;
    border-radius: 8px;
    padding: 20px;
    margin: 12px 0;
}

/* ── Recommendation card ────────────────────────────────────────────────── */
.rec-card {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 20px;
    height: 100%;
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session-state initialisation
# ---------------------------------------------------------------------------


def _init_state() -> None:
    defaults: dict = {
        "debug_result": None,
        "challenge_result": None,
        "eval_result": None,
        "learning_path_result": None,
        "hindsight_connected": True,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init_state()

# ---------------------------------------------------------------------------
# Shared services (cached so they are created only once per session)
# ---------------------------------------------------------------------------


@st.cache_resource
def get_memory_manager() -> MemoryManager:
    """Return a singleton MemoryManager."""
    return MemoryManager()


@st.cache_resource
def get_agent() -> CodingMentorAgent:
    """Return a singleton CodingMentorAgent."""
    return CodingMentorAgent(get_memory_manager())


memory_manager = get_memory_manager()
agent = get_agent()

LANGUAGES = [
    "Python",
    "JavaScript",
    "TypeScript",
    "Java",
    "C++",
    "C",
    "Go",
    "Rust",
    "Ruby",
    "Swift",
    "Kotlin",
    "PHP",
    "SQL",
    "Bash",
]

DIFFICULTIES = ["Easy", "Medium", "Hard"]

# ---------------------------------------------------------------------------
# Sidebar — Student Profile & Memory Dashboard
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("🧑‍💻 AI Coding Mentor")
    st.markdown("---")

    st.header("👤 Student Profile")
    student_id = st.text_input(
        "Student ID",
        value="student_001",
        help="Unique identifier for this student. Change to switch profiles.",
    )

    st.markdown("---")
    st.subheader("🧠 Memory Snapshot")

    with st.spinner("Loading memory profile…"):
        try:
            snapshot = memory_manager.get_profile_snapshot(student_id)
            st.session_state["hindsight_connected"] = True
        except Exception as exc:
            st.error(f"Could not load memory profile: {exc}")
            snapshot = {
                "languages": [],
                "mistakes": [],
                "behaviors": [],
                "topics": [],
                "session_count": 0,
                "fixes_count": 0,
            }

    # Language badges
    if snapshot["languages"]:
        lang_html = " ".join(
            f'<span class="badge-language">{lang}</span>'
            for lang in snapshot["languages"]
        )
        st.markdown(lang_html, unsafe_allow_html=True)
    else:
        st.caption("No languages recorded yet.")

    st.markdown("**📊 Stats**")
    col1, col2 = st.columns(2)
    col1.metric("Sessions", snapshot["session_count"])
    col2.metric("Fixes", snapshot["fixes_count"])

    # Last 3 mistakes
    recent_mistakes = snapshot["mistakes"][-3:]
    if recent_mistakes:
        st.markdown("**🐛 Recent Mistakes**")
        for m in reversed(recent_mistakes):
            lang = m.get("metadata", {}).get("language", "")
            lang_tag = f" `{lang}`" if lang else ""
            st.markdown(
                f'<div class="mentor-card" style="padding:10px;">'
                f'<span class="badge-mistake">BUG</span>'
                f"{lang_tag} {m.get('content', '')[:80]}"
                f"</div>",
                unsafe_allow_html=True,
            )

    # Behavior patterns
    if snapshot["behaviors"]:
        st.markdown("**🔎 Behavior Patterns**")
        for b in snapshot["behaviors"][-3:]:
            st.markdown(f"• {b.get('content', '')[:100]}")

    st.markdown("---")

    if st.button("🔄 Reset Memory", use_container_width=True):
        with st.spinner("Resetting memory…"):
            try:
                memory_manager.reset_memory(student_id)
                st.success("Memory reset successfully.")
                st.rerun()
            except Exception as exc:
                st.error(f"Reset failed: {exc}")

    st.markdown("---")
    # Connection status indicator
    if st.session_state.get("hindsight_connected", True):
        st.markdown("🟢 **Hindsight Cloud Connected**")
    else:
        st.markdown("🟡 **Using Local Fallback**")

# ---------------------------------------------------------------------------
# Main area — 4 tabs
# ---------------------------------------------------------------------------

tab1, tab2, tab3, tab4 = st.tabs(
    ["🐛 Debug My Code", "🎯 Coding Challenge", "🗺️ Learning Path", "📜 Raw Memory"]
)

# ============================================================================
# TAB 1 — Debug My Code
# ============================================================================

with tab1:
    st.header("🐛 Debug My Code")
    st.caption(
        "Paste your broken code below. The agent will analyse it using your full mistake history "
        "from Hindsight Cloud and return a personalised, memory-aware debug response."
    )

    left_col, right_col = st.columns([3, 2])

    with left_col:
        debug_language = st.selectbox(
            "Programming Language",
            LANGUAGES,
            key="debug_language",
        )
        debug_code = st.text_area(
            "Paste your broken code here",
            height=280,
            key="debug_code",
            placeholder=(
                "# Example broken Python code\n"
                "def find_max(arr):\n"
                "    max_val = arr[0]  # crashes if arr is empty\n"
                "    for i in range(len(arr)):\n"
                "        if arr[i] > max_val:\n"
                "            max_val = arr[i]\n"
                "    return max_val\n"
            ),
        )
        debug_error = st.text_area(
            "Error message (optional)",
            height=80,
            key="debug_error",
            placeholder="IndexError: list index out of range",
        )

    with right_col:
        st.markdown(
            """
<div class="mentor-card">
<strong>⚙️ How It Works — 9-Step Agent Loop</strong>
<ol style="margin-top:10px;padding-left:18px;line-height:1.8;">
<li>Read memory from Hindsight Cloud</li>
<li>Format past mistakes into context string</li>
<li>Inject code + error + memory into debug prompt</li>
<li>Call Groq LLM (temp=0.3, 2048 tokens)</li>
<li>Extract fixed code via regex</li>
<li>Detect behavior pattern heuristically</li>
<li>POST mistake, fix & behavior to Hindsight</li>
<li>Increment session & fix counters</li>
<li>Return structured result to Streamlit</li>
</ol>
</div>
""",
            unsafe_allow_html=True,
        )

    if st.button("🔍 Analyse & Debug", use_container_width=True, key="btn_debug"):
        if not debug_code.strip():
            st.warning("Please paste some code before clicking Analyse & Debug.")
        else:
            with st.spinner("🧠 Querying Hindsight memory and calling Groq…"):
                try:
                    result = agent.debug_code(
                        student_id=student_id,
                        language=debug_language,
                        code=debug_code,
                        error=debug_error,
                    )
                    st.session_state["debug_result"] = result
                except Exception as exc:
                    st.error(f"Debug failed: {exc}")
                    st.session_state["debug_result"] = None

    if st.session_state.get("debug_result"):
        res = st.session_state["debug_result"]
        st.markdown("---")
        st.subheader("📋 Analysis")
        st.markdown(res["analysis"])

        if res.get("fixed_code"):
            st.subheader("✅ Fixed Code")
            st.code(res["fixed_code"], language=debug_language.lower())

        if res.get("behavior_detected"):
            st.info(f"🔎 **Behavior Pattern Detected:** {res['behavior_detected']}")

        with st.expander("📂 Hindsight Memory Context Used"):
            st.json({"past_mistakes_summary": res.get("past_context", "")})

        st.success("✅ Session memory saved to Hindsight Cloud.")

# ============================================================================
# TAB 2 — Coding Challenge
# ============================================================================

with tab2:
    st.header("🎯 Adaptive Coding Challenge")
    st.caption(
        "The agent analyses your Hindsight memory to identify weak spots, then generates "
        "a personalised challenge targeting exactly those areas."
    )

    ch_col1, ch_col2 = st.columns(2)
    with ch_col1:
        challenge_language = st.selectbox("Language", LANGUAGES, key="ch_language")
    with ch_col2:
        difficulty_idx = st.select_slider(
            "Difficulty",
            options=DIFFICULTIES,
            value="Medium",
            key="ch_difficulty",
        )

    if st.button("🎲 Generate My Challenge", use_container_width=True, key="btn_challenge"):
        with st.spinner("🎯 Fetching weak areas from Hindsight and crafting a challenge…"):
            try:
                challenge = agent.generate_challenge(
                    student_id=student_id,
                    language=challenge_language,
                    difficulty=difficulty_idx,
                )
                st.session_state["challenge_result"] = challenge
                st.session_state["eval_result"] = None
            except Exception as exc:
                st.error(f"Challenge generation failed: {exc}")

    if st.session_state.get("challenge_result"):
        ch = st.session_state["challenge_result"]

        st.markdown(
            f'<div class="challenge-box">{ch["problem"]}</div>',
            unsafe_allow_html=True,
        )

        st.caption(f"⏱️ Time Limit: **{ch['time_limit']} minutes** &nbsp;|&nbsp; "
                   f"🎯 Targeting: *{ch['target_weakness']}*")

        if ch.get("starter_code"):
            st.subheader("📝 Starter Code")
            st.code(ch["starter_code"], language=challenge_language.lower())

        st.subheader("📤 Your Solution")
        solution_code = st.text_area(
            "Write your solution here",
            height=240,
            key="solution_code",
            placeholder=f"# Write your {challenge_language} solution here…",
        )

        if st.button("✅ Submit Solution", use_container_width=True, key="btn_submit"):
            if not solution_code.strip():
                st.warning("Please write a solution before submitting.")
            else:
                with st.spinner("🔍 Evaluating your solution…"):
                    try:
                        eval_result = agent.evaluate_solution(
                            student_id=student_id,
                            language=challenge_language,
                            challenge=ch["problem"],
                            solution=solution_code,
                        )
                        st.session_state["eval_result"] = eval_result
                    except Exception as exc:
                        st.error(f"Evaluation failed: {exc}")

    if st.session_state.get("eval_result"):
        ev = st.session_state["eval_result"]
        st.markdown("---")
        st.subheader("🏆 Evaluation Result")

        ev_col1, ev_col2 = st.columns([1, 3])
        with ev_col1:
            st.metric("Score", f"{ev.get('score', 0)}/100")
            if ev.get("passed"):
                st.success("✅ PASSED")
            else:
                st.error("❌ NOT PASSED")

        with ev_col2:
            st.markdown(f"**Feedback:** {ev.get('feedback', '')}")
            st.info(f"💡 **Improvement Tip:** {ev.get('improvement_tip', '')}")

# ============================================================================
# TAB 3 — Learning Path
# ============================================================================

with tab3:
    st.header("🗺️ Personalised Learning Path")
    st.caption(
        "Based on your full Hindsight memory — projects, languages, and behavior — "
        "the agent recommends exactly 3 next learning steps."
    )

    if st.button("🗺️ Generate My Learning Path", use_container_width=True, key="btn_path"):
        with st.spinner("📚 Analysing your history and generating recommendations…"):
            try:
                path_result = agent.recommend_learning_path(student_id)
                st.session_state["learning_path_result"] = path_result
            except Exception as exc:
                st.error(f"Learning path generation failed: {exc}")

    if st.session_state.get("learning_path_result"):
        recs = st.session_state["learning_path_result"].get("recommendations", [])
        if not recs:
            st.info("No recommendations generated. Try debugging some code first to build your memory profile.")
        else:
            st.markdown("---")
            rec_cols = st.columns(len(recs))
            for col, rec in zip(rec_cols, recs):
                resource_type = rec.get("resource_type", "Resource")
                priority = rec.get("priority", "—")
                with col:
                    st.markdown(
                        f'<div class="rec-card">'
                        f'<div style="margin-bottom:8px;">'
                        f'<span class="badge-resource">{resource_type}</span>'
                        f'&nbsp;<small style="color:#8b949e;">Priority {priority}</small>'
                        f'</div>'
                        f'<strong style="font-size:1.05rem;">{rec.get("title", "")}</strong>'
                        f'<p style="margin-top:8px;color:#8b949e;font-size:0.9rem;">'
                        f'{rec.get("reason", "")}'
                        f'</p>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

# ============================================================================
# TAB 4 — Raw Memory
# ============================================================================

with tab4:
    st.header("📜 Raw Memory Store")
    st.caption(
        "Live view of all memory entries stored in Hindsight Cloud for this student."
    )

    with st.spinner("Fetching from Hindsight Cloud…"):
        try:
            all_memories = memory_manager.list_all_memories(student_id)
        except Exception as exc:
            st.error(f"Could not fetch memories: {exc}")
            all_memories = []

    st.metric("Total Memory Entries", len(all_memories))

    if all_memories:
        st.json(all_memories)
        memory_json = json.dumps(all_memories, indent=2)
        st.download_button(
            label="⬇️ Export Memory as JSON",
            data=memory_json,
            file_name=f"{student_id}_memory.json",
            mime="application/json",
        )
    else:
        st.info(
            "No memories found for this student yet. "
            "Start by debugging some code in the 🐛 Debug tab!"
        )
