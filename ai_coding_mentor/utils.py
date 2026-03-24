"""
utils.py
========
Utility helpers for the AI Coding Practice Mentor.
"""

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

_LANGUAGE_KEYWORDS: dict[str, list[str]] = {
    "Python": [
        "def ", "import ", "print(", "elif ", "None", "__init__", "self.", "lambda ",
        "range(", "len(", "dict(", "list(", "tuple(",
    ],
    "JavaScript": [
        "function ", "const ", "let ", "var ", "=>", "console.log", "document.",
        "window.", "require(", "module.exports",
    ],
    "TypeScript": ["interface ", ": string", ": number", ": boolean", "type ", "as "],
    "Java": [
        "public class ", "System.out.println", "public static void main",
        "import java.", "new ArrayList", "throws ",
    ],
    "C++": [
        "#include", "std::", "cout <<", "cin >>", "int main(", "nullptr", "vector<",
    ],
    "C": ["#include <stdio.h>", "printf(", "scanf(", "int main(", "malloc(", "free("],
    "Rust": ["fn main(", "let mut ", "println!(", "use std::", "impl ", "enum ", "match "],
    "Go": ["func main()", "package main", "import \"fmt\"", "fmt.Println", ":= "],
    "Ruby": ["def ", "puts ", "require ", "end\n", "attr_accessor", ".each do"],
    "Swift": ["import UIKit", "var ", "let ", "func ", "print(", "guard let"],
    "Kotlin": ["fun main(", "println(", "val ", "var ", "data class ", "?."],
    "PHP": ["<?php", "echo ", "$", "function ", "->", "array("],
    "SQL": ["SELECT ", "FROM ", "WHERE ", "INSERT INTO", "CREATE TABLE", "JOIN "],
    "Bash": ["#!/bin/bash", "echo ", "fi\n", "then\n", "do\n", "done\n"],
}


def detect_language(code: str) -> str:
    """
    Heuristically detect the programming language of *code*.

    Scores each candidate language by counting how many of its characteristic
    keywords appear in the code and returns the language with the highest score.
    Falls back to ``"Unknown"`` if no language scores above zero.

    Parameters
    ----------
    code : Source code string to analyse.

    Returns
    -------
    str
        Detected language name or ``"Unknown"``.
    """
    scores: dict[str, int] = {}
    for lang, keywords in _LANGUAGE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in code)
        if score > 0:
            scores[lang] = score

    if not scores:
        return "Unknown"
    return max(scores, key=lambda lang: scores[lang])


# ---------------------------------------------------------------------------
# Code extraction from LLM markdown responses
# ---------------------------------------------------------------------------

_CODE_FENCE_RE = re.compile(r"```[\w]*\n(.*?)```", re.DOTALL)


def extract_code_blocks(text: str) -> list[str]:
    """
    Extract all fenced code blocks from *text*.

    Returns a list of code strings (without the fence markers).

    Parameters
    ----------
    text : Raw LLM response or any markdown string.
    """
    return [match.group(1) for match in _CODE_FENCE_RE.finditer(text)]


def extract_first_code_block(text: str) -> str:
    """
    Return the first fenced code block found in *text*, or an empty string.

    Parameters
    ----------
    text : Raw LLM response or any markdown string.
    """
    blocks = extract_code_blocks(text)
    return blocks[0] if blocks else ""


# ---------------------------------------------------------------------------
# JSON extraction (for LLM responses that embed JSON in markdown)
# ---------------------------------------------------------------------------

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json_from_text(text: str) -> str:
    """
    Strip markdown fences from an LLM response to obtain raw JSON.

    If no fence is found, the original *text* is returned stripped.

    Parameters
    ----------
    text : Raw LLM response potentially wrapped in markdown fences.
    """
    match = _JSON_FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


# ---------------------------------------------------------------------------
# Challenge response parsing helpers
# ---------------------------------------------------------------------------

_TIME_LIMIT_RE = re.compile(r"[Tt]ime\s+[Ll]imit:\s*(\d+)\s*minute", re.IGNORECASE)


def extract_time_limit(text: str, default: int = 5) -> int:
    """
    Parse a time limit (in minutes) from a challenge response string.

    Parameters
    ----------
    text    : Challenge text from the LLM.
    default : Value to return when no time limit is found.
    """
    match = _TIME_LIMIT_RE.search(text)
    if match:
        return int(match.group(1))
    return default


def split_challenge_and_code(text: str) -> tuple[str, str]:
    """
    Split a challenge response into (problem_statement, starter_code).

    The *starter_code* is taken from the first fenced code block; the
    *problem_statement* is the text that precedes it.

    Parameters
    ----------
    text : Full LLM challenge response.

    Returns
    -------
    tuple[str, str]
        ``(problem_statement, starter_code)``
    """
    first_fence = text.find("```")
    if first_fence == -1:
        return text.strip(), ""

    problem = text[:first_fence].strip()
    starter_code = extract_first_code_block(text)
    return problem, starter_code
