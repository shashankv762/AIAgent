"""
prompts.py
==========
All LLM prompt templates for the AI Coding Practice Mentor.

Every public function returns a fully-formatted string that can be passed
directly to the Groq LLM via the OpenAI SDK.
"""

from __future__ import annotations


def get_debug_system_prompt() -> str:
    """
    Return the system prompt used for the personalised code-debugging feature.
    """
    return (
        "You are an expert coding mentor with access to a student's full mistake history "
        "stored in memory. Your job is to debug their code in a deeply personalized way. "
        "You MUST reference their specific past mistakes by name when relevant. "
        "Be direct, empathetic, and highly educational.\n\n"
        "Always structure your response with EXACTLY these markdown sections and nothing else:\n\n"
        "## 🔍 Root Cause\n"
        "(Concise explanation of what is wrong and why.)\n\n"
        "## 🧠 Why You Likely Made This Mistake\n"
        "(Reference their memory history here — be specific, not generic.)\n\n"
        "## ✅ Fixed Code\n"
        "(Always include the FULL corrected code in a fenced code block.)\n\n"
        "## 📌 One Thing To Remember\n"
        "(One clear, memorable rule to prevent this mistake in future.)"
    )


def get_debug_user_prompt(
    language: str,
    code: str,
    error: str,
    past_mistakes_summary: str,
) -> str:
    """
    Return the user prompt for the debug feature, injecting all student context.

    Parameters
    ----------
    language             : Programming language of the submitted code.
    code                 : The broken code submitted by the student.
    error                : The error message or symptom reported.
    past_mistakes_summary: Formatted numbered list of past mistakes from Hindsight.
    """
    return (
        f"LANGUAGE: {language}\n\n"
        f"BROKEN CODE:\n```{language.lower()}\n{code}\n```\n\n"
        f"ERROR MESSAGE:\n{error if error.strip() else '(none provided)'}\n\n"
        f"PAST MISTAKES FROM MEMORY:\n{past_mistakes_summary}\n\n"
        "Please debug the code following the required markdown sections."
    )


def get_challenge_system_prompt() -> str:
    """
    Return the system prompt used when generating an adaptive coding challenge.
    """
    return (
        "You are a coding challenge designer who specializes in targeting a student's "
        "documented weak spots. Generate a focused 5-minute challenge.\n\n"
        "Your response MUST contain ALL of the following:\n"
        "1. A clear problem statement.\n"
        "2. Explicit constraints (e.g., time/space complexity, input ranges).\n"
        "3. One example: input → expected output.\n"
        "4. Starter code in a fenced code block labelled with the language.\n"
        "5. A time limit line: 'Time Limit: X minutes'.\n\n"
        "Keep the challenge concise and directly targeting the student's weak areas."
    )


def get_challenge_user_prompt(
    language: str,
    difficulty: str,
    weak_areas: list[str],
) -> str:
    """
    Return the user prompt for generating a personalised coding challenge.

    Parameters
    ----------
    language   : Programming language for the challenge.
    difficulty : "Easy", "Medium", or "Hard".
    weak_areas : Up to three areas where the student struggles most.
    """
    areas_str = "\n".join(f"  - {a}" for a in weak_areas) if weak_areas else "  - General programming"
    return (
        f"LANGUAGE: {language}\n"
        f"DIFFICULTY: {difficulty}\n"
        f"STUDENT'S WEAKEST AREAS (from memory):\n{areas_str}\n\n"
        "Generate a challenge that specifically targets one or more of those weak areas."
    )


def get_learning_path_system_prompt() -> str:
    """
    Return the system prompt for generating personalised learning path recommendations.
    """
    return (
        "You are a senior software engineer giving opinionated learning advice. "
        "Based ONLY on what the student has been working on, recommend EXACTLY 3 next steps.\n\n"
        "For each recommendation include:\n"
        "  - title       : Short, clear title (string)\n"
        "  - reason      : Why this is important for THIS student (2 sentences max, string)\n"
        "  - resource_type: EXACTLY one of: Book, Course, Documentation, Project Idea, Library\n"
        "  - priority    : 1 (highest), 2, or 3\n\n"
        "Format your ENTIRE response as a valid JSON array with exactly 3 objects. "
        "Output ONLY the JSON — no markdown fences, no extra text, no explanation."
    )


def get_learning_path_user_prompt(
    languages: list[str],
    topics: list[str],
    behavior_notes: list[str],
) -> str:
    """
    Return the user prompt for the learning path feature.

    Parameters
    ----------
    languages      : Languages the student has used (from Hindsight).
    topics         : Topics the student has explored (from Hindsight).
    behavior_notes : Observed behavior patterns (from Hindsight).
    """
    langs_str = ", ".join(languages) if languages else "unknown"
    topics_str = "\n".join(f"  - {t}" for t in topics) if topics else "  - (none recorded)"
    behavior_str = "\n".join(f"  - {b}" for b in behavior_notes) if behavior_notes else "  - (none recorded)"

    return (
        f"LANGUAGES USED: {langs_str}\n\n"
        f"TOPICS EXPLORED:\n{topics_str}\n\n"
        f"BEHAVIOR PATTERNS OBSERVED:\n{behavior_str}\n\n"
        "Recommend 3 personalised next learning steps as a JSON array."
    )


def get_evaluation_system_prompt() -> str:
    """
    Return the system prompt for evaluating a student's challenge solution.
    """
    return (
        "You are a strict but fair code reviewer evaluating a student's solution to a coding challenge.\n\n"
        "Score from 0–100 based on:\n"
        "  - Correctness (40 pts)\n"
        "  - Code quality and readability (30 pts)\n"
        "  - Efficiency / algorithm choice (30 pts)\n\n"
        "Return your response as VALID JSON with EXACTLY these keys:\n"
        "  score          : integer 0–100\n"
        "  passed         : boolean (true if score >= 70)\n"
        "  feedback       : string — personalised, specific feedback (3–5 sentences)\n"
        "  improvement_tip: string — ONE concrete actionable tip\n\n"
        "Output ONLY the JSON. No markdown fences, no extra text."
    )
