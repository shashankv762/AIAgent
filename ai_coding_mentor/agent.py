"""
agent.py
========
CodingMentorAgent — the central AI reasoning loop for the AI Coding Practice Mentor.

Implements an OpenClaw-style loop:
  Step 1 → Read memory   (Hindsight Cloud)
  Step 2 → Build context (format memory into a readable string)
  Step 3 → Build prompt  (inject code + error + memory context)
  Step 4 → Call Groq     (OpenAI SDK pointing at Groq base URL)
  Step 5 → Parse response (regex extraction of fixed code)
  Step 6 → Detect pattern (heuristic + optional short Groq call)
  Step 7 → Write memory  (POST to Hindsight Cloud)
  Step 8 → Update counters
  Step 9 → Return result (dict for Streamlit rendering)
"""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from openai import OpenAI

from memory_manager import MemoryManager
from prompts import (
    get_challenge_system_prompt,
    get_challenge_user_prompt,
    get_debug_system_prompt,
    get_debug_user_prompt,
    get_evaluation_system_prompt,
    get_learning_path_system_prompt,
    get_learning_path_user_prompt,
)
from utils import extract_first_code_block, extract_json_from_text, extract_time_limit, split_challenge_and_code

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise EnvironmentError(
        "GROQ_API_KEY is not set. Add it to your .env file or environment variables."
    )
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"


class CodingMentorAgent:
    """
    The AI agent that orchestrates memory retrieval, LLM calls, and memory writes.

    Uses the OpenAI Python SDK pointed at Groq's OpenAI-compatible API endpoint.
    Does NOT use LangChain, LlamaIndex, or any third-party agent framework.
    """

    def __init__(self, memory_manager: MemoryManager) -> None:
        """
        Initialise the agent.

        Parameters
        ----------
        memory_manager : Shared MemoryManager instance for reading/writing student memory.
        """
        self.memory_manager = memory_manager
        self.client = OpenAI(
            api_key=GROQ_API_KEY,
            base_url=GROQ_BASE_URL,
        )

    # ---------------------------------------------------------------------- #
    # Internal helpers                                                         #
    # ---------------------------------------------------------------------- #

    def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str:
        """
        Send a chat completion request to Groq and return the response text.

        Parameters
        ----------
        system_prompt : The system message.
        user_prompt   : The user message.
        temperature   : Sampling temperature.
        max_tokens    : Maximum tokens in the response.
        """
        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    # ---------------------------------------------------------------------- #
    # Debug                                                                    #
    # ---------------------------------------------------------------------- #

    def debug_code(
        self,
        student_id: str,
        language: str,
        code: str,
        error: str,
    ) -> dict[str, Any]:
        """
        Run the 9-step agent loop to debug student code and save the session.

        Parameters
        ----------
        student_id : Unique identifier for the student.
        language   : Programming language of the submitted code.
        code       : The broken source code.
        error      : The error message or symptom.

        Returns
        -------
        dict with keys: analysis, fixed_code, past_context, behavior_detected
        """
        # Step 1 — Read memory
        past_context = self.memory_manager.get_mistake_summary(student_id)

        # Step 2 — Build context  (already formatted by get_mistake_summary)

        # Step 3 — Build prompt
        user_prompt = get_debug_user_prompt(language, code, error, past_context)

        # Step 4 — Call Groq
        analysis = self._call_llm(
            system_prompt=get_debug_system_prompt(),
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=2048,
        )

        # Step 5 — Parse response
        fixed_code = extract_first_code_block(analysis)

        # Step 6 — Detect pattern
        behavior_detected = self.detect_behavior_pattern(code, language)

        # Derive a short mistake description from the analysis
        # (use the first non-empty line after "## 🔍 Root Cause")
        mistake_description = _extract_root_cause(analysis) or f"Bug in {language} code"

        # Step 7 — Write memory  (Step 8 counters are implicit in save_full_session)
        self.memory_manager.save_full_session(
            student_id=student_id,
            language=language,
            mistake_description=mistake_description,
            code_snippet=code[:500],
            fix=fixed_code or analysis[:300],
            behavior_note=behavior_detected,
        )

        # Step 9 — Return result
        return {
            "analysis": analysis,
            "fixed_code": fixed_code,
            "past_context": past_context,
            "behavior_detected": behavior_detected,
        }

    # ---------------------------------------------------------------------- #
    # Challenge                                                                #
    # ---------------------------------------------------------------------- #

    def generate_challenge(
        self,
        student_id: str,
        language: str,
        difficulty: str,
    ) -> dict[str, Any]:
        """
        Generate an adaptive coding challenge targeting the student's weak areas.

        Parameters
        ----------
        student_id : Unique identifier for the student.
        language   : Programming language for the challenge.
        difficulty : "Easy", "Medium", or "Hard".

        Returns
        -------
        dict with keys: problem, starter_code, time_limit, target_weakness
        """
        # Step 1 — Query weak areas
        weak_memories = self.memory_manager.query_memories(
            student_id,
            "what are the weakest areas and most repeated mistakes for this student",
            top_k=5,
        )

        # Step 2 — Extract top 3 weak areas
        weak_areas: list[str] = []
        for mem in weak_memories[:3]:
            content = mem.get("content", "").strip()
            if content:
                weak_areas.append(content)

        # Step 3 — Build prompt
        user_prompt = get_challenge_user_prompt(language, difficulty, weak_areas)

        # Step 4 — Call Groq
        raw_challenge = self._call_llm(
            system_prompt=get_challenge_system_prompt(),
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=1500,
        )

        # Step 5 — Parse response
        problem, starter_code = split_challenge_and_code(raw_challenge)
        time_limit = extract_time_limit(raw_challenge)

        return {
            "problem": problem,
            "starter_code": starter_code,
            "time_limit": time_limit,
            "target_weakness": weak_areas[0] if weak_areas else "general programming",
            "raw": raw_challenge,
        }

    def evaluate_solution(
        self,
        student_id: str,
        language: str,
        challenge: str,
        solution: str,
    ) -> dict[str, Any]:
        """
        Evaluate the student's solution to a coding challenge.

        Parameters
        ----------
        student_id : Unique identifier for the student.
        language   : Programming language of the solution.
        challenge  : The original challenge problem statement.
        solution   : The student's submitted solution code.

        Returns
        -------
        dict with keys: score, feedback, passed, improvement_tip
        """
        user_prompt = (
            f"LANGUAGE: {language}\n\n"
            f"CHALLENGE:\n{challenge}\n\n"
            f"STUDENT SOLUTION:\n```{language.lower()}\n{solution}\n```\n\n"
            "Evaluate the solution and return JSON as specified."
        )

        # Step 1 — Evaluate
        raw = self._call_llm(
            system_prompt=get_evaluation_system_prompt(),
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=800,
        )

        # Step 2 — Parse JSON response
        try:
            clean = extract_json_from_text(raw)
            result: dict[str, Any] = json.loads(clean)
        except (json.JSONDecodeError, ValueError):
            result = {
                "score": 0,
                "passed": False,
                "feedback": raw,
                "improvement_tip": "Unable to parse evaluation. Please try again.",
            }

        # Step 3 — Write positive memory on pass
        if result.get("passed"):
            topic = _guess_topic(challenge)
            self.memory_manager.write_memory(
                student_id,
                f"Successfully solved a {difficulty_from_challenge(challenge)} {topic} challenge in {language}",
                memory_type="topic",
                language=language,
            )

        return result

    # ---------------------------------------------------------------------- #
    # Learning path                                                            #
    # ---------------------------------------------------------------------- #

    def recommend_learning_path(self, student_id: str) -> dict[str, Any]:
        """
        Generate 3 personalised learning-path recommendations based on Hindsight memory.

        Returns
        -------
        dict with key: recommendations — list of dicts with title, reason,
                       resource_type, priority
        """
        # Step 1 — Query Hindsight for student context
        context_memories = self.memory_manager.query_memories(
            student_id,
            "what topics, languages, and projects has this student explored",
            top_k=15,
        )

        profile = self.memory_manager.get_profile_snapshot(student_id)

        # Collect language, topic, and behavior info
        languages = profile.get("languages", [])
        topics = [m.get("content", "") for m in profile.get("topics", [])]
        behaviors = [m.get("content", "") for m in profile.get("behaviors", [])]

        # Also fold in queried context memories not already captured
        for mem in context_memories:
            content = mem.get("content", "").strip()
            if content and content not in topics:
                topics.append(content)

        # Step 2 — Build prompt
        user_prompt = get_learning_path_user_prompt(languages, topics[:10], behaviors[:5])

        # Step 3 — Call Groq
        raw = self._call_llm(
            system_prompt=get_learning_path_system_prompt(),
            user_prompt=user_prompt,
            temperature=0.5,
            max_tokens=1000,
        )

        # Step 4 — Parse JSON response
        try:
            clean = extract_json_from_text(raw)
            recommendations: list[dict[str, Any]] = json.loads(clean)
            if not isinstance(recommendations, list):
                recommendations = []
        except (json.JSONDecodeError, ValueError):
            recommendations = []

        # Step 5 — Ensure exactly 3 recommendations, fill with defaults if needed
        recommendations = recommendations[:3]
        while len(recommendations) < 3:
            recommendations.append(
                {
                    "title": "Keep practising!",
                    "reason": "Build more projects to generate a richer memory profile.",
                    "resource_type": "Project Idea",
                    "priority": len(recommendations) + 1,
                }
            )

        return {"recommendations": recommendations}

    # ---------------------------------------------------------------------- #
    # Behaviour detection                                                      #
    # ---------------------------------------------------------------------- #

    def detect_behavior_pattern(self, code: str, language: str) -> str | None:
        """
        Detect common coding behaviour patterns using heuristics.

        Heuristics checked (in order):
          1. Deeply nested loops          → brute-force tendency
          2. No try/except (Python) or try/catch (others) → missing error handling
          3. No comments at all           → lacks documentation habit
          4. Very long functions (>50 lines) → monolithic function style

        If a heuristic fires, a short Groq call is made to phrase the pattern
        as a single readable sentence.

        Parameters
        ----------
        code     : Source code submitted by the student.
        language : Programming language of the code.

        Returns
        -------
        str or None
            A single-sentence description of the detected pattern, or ``None``.
        """
        pattern_raw: str | None = None

        lines = code.splitlines()

        # Heuristic 1 — nested loops (look for 3+ levels of indentation on loop keywords)
        loop_keywords = ("for ", "while ")
        indent_depths = []
        for line in lines:
            stripped = line.lstrip()
            if any(stripped.startswith(kw) for kw in loop_keywords):
                indent = len(line) - len(stripped)
                indent_depths.append(indent)
        if len(indent_depths) >= 2 and (max(indent_depths) - min(indent_depths)) >= 8:
            pattern_raw = "Tends to use brute force O(n²) solutions with nested loops"

        # Heuristic 2 — no error handling
        if pattern_raw is None:
            has_error_handling = (
                "try:" in code
                or "except" in code
                or "try {" in code
                or "catch" in code
            )
            if not has_error_handling and len(lines) > 5:
                pattern_raw = "Does not implement error handling"

        # Heuristic 3 — no comments
        if pattern_raw is None:
            has_comment = any(
                stripped.startswith("#")
                or stripped.startswith("//")
                or stripped.startswith("/*")
                or stripped.startswith("*")
                for stripped in (line.lstrip() for line in lines)
            )
            if not has_comment and len(lines) > 10:
                pattern_raw = "Does not write documentation or comments"

        # Heuristic 4 — monolithic long functions
        if pattern_raw is None:
            func_keywords = ("def ", "function ", "func ", "void ", "int ", "public ")
            current_func_start: int | None = None
            for i, line in enumerate(lines):
                stripped = line.lstrip()
                if any(stripped.startswith(kw) for kw in func_keywords):
                    if current_func_start is not None and (i - current_func_start) > 50:
                        pattern_raw = "Writes monolithic functions without decomposition"
                        break
                    current_func_start = i

        if pattern_raw is None:
            return None

        # Optionally refine with a short Groq call
        try:
            refined = self._call_llm(
                system_prompt=(
                    "You describe a student's coding behaviour pattern in exactly ONE sentence. "
                    "Be specific and educational. Return only the single sentence."
                ),
                user_prompt=(
                    f"Pattern detected in {language} code: {pattern_raw}\n\n"
                    "Describe this pattern in one sentence as feedback for the student."
                ),
                temperature=0.4,
                max_tokens=80,
            )
            return refined.strip().rstrip(".")
        except Exception:
            return pattern_raw


# ---------------------------------------------------------------------------
# Private module-level helpers
# ---------------------------------------------------------------------------


def _extract_root_cause(analysis: str) -> str:
    """
    Pull the first substantive line after the Root Cause heading.
    """
    marker = "## 🔍 Root Cause"
    idx = analysis.find(marker)
    if idx == -1:
        return ""
    after = analysis[idx + len(marker):].lstrip()
    for line in after.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line[:200]
    return ""


def _guess_topic(challenge_text: str) -> str:
    """
    Guess a short topic label from a challenge's problem text.
    """
    keywords = [
        "array", "string", "linked list", "tree", "graph", "sorting",
        "searching", "dynamic programming", "recursion", "hash map",
        "stack", "queue", "binary search",
    ]
    lower = challenge_text.lower()
    for kw in keywords:
        if kw in lower:
            return kw
    return "programming"


def difficulty_from_challenge(challenge_text: str) -> str:
    """
    Try to extract the difficulty level from a challenge string.
    """
    lower = challenge_text.lower()
    for level in ("easy", "medium", "hard"):
        if level in lower:
            return level
    return "coding"
