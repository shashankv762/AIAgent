"""
memory_manager.py
=================
Manages persistent student memory using Hindsight Cloud as the primary store
and a local JSON file as a fallback when the remote API is unreachable.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import requests
import streamlit as st

HINDSIGHT_BASE_URL = "https://api.hindsight.vectorize.io"
HINDSIGHT_API_KEY = os.getenv(
    "HINDSIGHT_API_KEY",
    "hsk_7328b91d7064aad7f89890f9219e1369_184daeecf11c96fb",
)
LOCAL_MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory_store.json")


def _headers() -> dict[str, str]:
    """Return the required Hindsight Cloud request headers."""
    return {
        "Authorization": f"Bearer {HINDSIGHT_API_KEY}",
        "Content-Type": "application/json",
    }


def _load_local() -> dict[str, Any]:
    """Load the local JSON fallback store, creating it if it does not exist."""
    if not os.path.exists(LOCAL_MEMORY_FILE):
        with open(LOCAL_MEMORY_FILE, "w") as f:
            json.dump({}, f)
        return {}
    try:
        with open(LOCAL_MEMORY_FILE, "r") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_local(data: dict[str, Any]) -> None:
    """Persist the local fallback store to disk."""
    with open(LOCAL_MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _warn_fallback(action: str) -> None:
    """Display a Streamlit warning that the app is using local fallback storage."""
    st.warning(
        f"⚠️ Hindsight Cloud unreachable during '{action}'. "
        "Using local JSON fallback instead."
    )


class MemoryManager:
    """
    Manages student memory with two layers:

    Layer 1 (primary)  – Hindsight Cloud: remote, persistent, vector-backed.
    Layer 2 (fallback) – Local JSON file: used when Layer 1 is unreachable.

    All public methods transparently handle the fallback and show Streamlit
    warnings so the user is always aware of which storage layer is active.
    """

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _local_add(self, student_id: str, entry: dict[str, Any]) -> None:
        """Append a memory entry to the local JSON store for *student_id*."""
        data = _load_local()
        if student_id not in data:
            data[student_id] = []
        data[student_id].append(entry)
        _save_local(data)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def write_memory(
        self,
        student_id: str,
        content: str,
        memory_type: str,
        language: str | None = None,
    ) -> None:
        """
        Save a single memory entry for *student_id*.

        Parameters
        ----------
        student_id  : Unique identifier for the student.
        content     : Natural-language description of the memory.
        memory_type : One of "mistake", "behavior", "language", "fix", "topic".
        language    : Optional programming language associated with the memory.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        metadata: dict[str, Any] = {
            "type": memory_type,
            "timestamp": timestamp,
        }
        if language:
            metadata["language"] = language

        payload = {
            "user_id": student_id,
            "content": content,
            "metadata": metadata,
        }

        # Mirror-write to local JSON regardless of remote success
        local_entry = {"content": content, "metadata": metadata}
        self._local_add(student_id, local_entry)

        try:
            resp = requests.post(
                f"{HINDSIGHT_BASE_URL}/v1/memories",
                headers=_headers(),
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
        except Exception:
            _warn_fallback("write_memory")

    def query_memories(
        self,
        student_id: str,
        query: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Retrieve the most relevant memories for *student_id* matching *query*.

        Falls back to a simple keyword-match against the local JSON store if the
        remote API is unreachable.

        Returns a list of dicts with keys ``content`` and ``metadata``.
        """
        payload = {
            "user_id": student_id,
            "query": query,
            "top_k": top_k,
        }
        try:
            resp = requests.post(
                f"{HINDSIGHT_BASE_URL}/v1/memories/query",
                headers=_headers(),
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
            result = resp.json()
            return result.get("memories", [])
        except Exception:
            _warn_fallback("query_memories")
            # Keyword-based fallback
            data = _load_local()
            entries: list[dict[str, Any]] = data.get(student_id, [])
            keywords = query.lower().split()
            matched: list[dict[str, Any]] = []
            for entry in entries:
                text = entry.get("content", "").lower()
                if any(kw in text for kw in keywords):
                    matched.append(entry)
            return matched[:top_k]

    def list_all_memories(self, student_id: str) -> list[dict[str, Any]]:
        """
        Return every stored memory for *student_id*.

        Falls back to the local JSON store on API failure.
        """
        try:
            resp = requests.get(
                f"{HINDSIGHT_BASE_URL}/v1/memories",
                headers=_headers(),
                params={"user_id": student_id},
                timeout=10,
            )
            resp.raise_for_status()
            result = resp.json()
            # Hindsight may return { "memories": [...] } or a bare list
            if isinstance(result, list):
                return result
            return result.get("memories", [])
        except Exception:
            _warn_fallback("list_all_memories")
            data = _load_local()
            return data.get(student_id, [])

    def reset_memory(self, student_id: str) -> None:
        """
        Delete ALL memories for *student_id* from both remote and local stores.
        """
        # Always clear local store
        data = _load_local()
        if student_id in data:
            del data[student_id]
        _save_local(data)

        try:
            resp = requests.delete(
                f"{HINDSIGHT_BASE_URL}/v1/memories",
                headers=_headers(),
                params={"user_id": student_id},
                timeout=10,
            )
            resp.raise_for_status()
        except Exception:
            _warn_fallback("reset_memory")

    def get_mistake_summary(self, student_id: str) -> str:
        """
        Return a formatted numbered list of past mistakes for *student_id*.

        This string is injected directly into the LLM debug prompt to provide
        personalised context about the student's history.
        """
        memories = self.query_memories(
            student_id,
            "what mistakes and bugs has this student made recently",
            top_k=10,
        )
        if not memories:
            return "No past mistakes recorded yet."

        lines: list[str] = []
        for i, mem in enumerate(memories, start=1):
            meta = mem.get("metadata", {})
            lang = meta.get("language", "")
            lang_tag = f" [{lang}]" if lang else ""
            lines.append(f"{i}.{lang_tag} {mem.get('content', '')}")
        return "\n".join(lines)

    def get_profile_snapshot(self, student_id: str) -> dict[str, Any]:
        """
        Build a bucketed profile snapshot for the memory dashboard.

        Returns a dict with keys:
            languages    – unique language strings
            mistakes     – memory entries of type "mistake"
            behaviors    – memory entries of type "behavior"
            topics       – memory entries of type "topic"
            session_count – total number of sessions (mistakes)
            fixes_count   – total number of fixes recorded
        """
        all_memories = self.list_all_memories(student_id)

        languages: list[str] = []
        mistakes: list[dict[str, Any]] = []
        behaviors: list[dict[str, Any]] = []
        topics: list[dict[str, Any]] = []
        fixes_count = 0

        for mem in all_memories:
            meta = mem.get("metadata", {})
            mem_type = meta.get("type", "")
            lang = meta.get("language", "")

            if mem_type == "language" and lang and lang not in languages:
                languages.append(lang)
            elif mem_type == "mistake":
                mistakes.append(mem)
                if lang and lang not in languages:
                    languages.append(lang)
            elif mem_type == "behavior":
                behaviors.append(mem)
            elif mem_type == "topic":
                topics.append(mem)
            elif mem_type == "fix":
                fixes_count += 1

        return {
            "languages": languages,
            "mistakes": mistakes,
            "behaviors": behaviors,
            "topics": topics,
            "session_count": len(mistakes),
            "fixes_count": fixes_count,
        }

    def save_full_session(
        self,
        student_id: str,
        language: str,
        mistake_description: str,
        code_snippet: str,
        fix: str,
        behavior_note: str | None = None,
    ) -> None:
        """
        Persist all memory facets captured during a single debug session.

        Writes up to four memory entries:
          1. The mistake (type="mistake")
          2. The fix     (type="fix")
          3. The language if new (type="language")
          4. The behavior note if provided (type="behavior")
        """
        # 1. Mistake
        self.write_memory(
            student_id,
            mistake_description,
            memory_type="mistake",
            language=language,
        )
        # 2. Fix
        self.write_memory(
            student_id,
            f"Fix applied: {fix[:300]}",
            memory_type="fix",
            language=language,
        )
        # 3. Language
        self.write_memory(
            student_id,
            f"Student used {language}",
            memory_type="language",
            language=language,
        )
        # 4. Behavior (optional)
        if behavior_note:
            self.write_memory(
                student_id,
                behavior_note,
                memory_type="behavior",
                language=language,
            )
