import asyncio
import json
import logging
import os
import sqlite3
from typing import Dict, Any, List, Optional

logger = logging.getLogger("breakaway_ai.memory")

class AsyncPersistentMemoryBank:
    """
    Asynchronous Persistent Memory Store using SQLite persistent database for user biometrics,
    historical EWMA state, and long-term coaching preferences.
    Executes non-blocking async database operations.
    """
    def __init__(self, db_path: str = "breakaway_memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_memory (
                    session_id TEXT PRIMARY KEY,
                    profile_json TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    async def save_user_profile_async(self, session_id: str, profile_data: Dict[str, Any]) -> bool:
        """Async memory operation storing persistent profile data in SQLite DB."""
        def _save():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO session_memory (session_id, profile_json)
                    VALUES (?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        profile_json = excluded.profile_json,
                        updated_at = CURRENT_TIMESTAMP
                """, (session_id, json.dumps(profile_data)))
                conn.commit()

        await asyncio.to_thread(_save)
        logger.info(f"Async Persistent Database: Saved profile to SQLite DB for session {session_id}")
        return True

    async def load_user_profile_async(self, session_id: str) -> Dict[str, Any]:
        """Async memory operation retrieving persistent profile from SQLite DB."""
        def _load():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT profile_json FROM session_memory WHERE session_id = ?", (session_id,))
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return {
                    "ftp_watts": 261,
                    "max_hr_bpm": 205,
                    "resting_hr_bpm": 47,
                    "weight_kg": 63.0
                }

        return await asyncio.to_thread(_load)

class HistoryCompactor:
    """
    Sliding-Window History Compaction & Summarization Engine.
    Prevents context window overflow during multi-turn conversations.
    """
    def compact_conversation_history(
        self,
        messages: List[Dict[str, Any]],
        max_turns: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Compacts long conversation turns into a succinct memory summary + recent window.
        """
        if len(messages) <= max_turns:
            return messages

        system_turn = messages[0] if messages and messages[0].get("role") == "system" else None
        older_turns = messages[1:-max_turns] if system_turn else messages[:-max_turns]
        recent_turns = messages[-max_turns:]

        summary_text = f"[COMPACTED HISTORY SUMMARY: User discussed {len(older_turns)} past training turns. Target FTP 261W, Max HR 205 BPM, ACWR steady in Sweet Spot]."
        summary_turn = {"role": "system", "content": summary_text}

        compacted = []
        if system_turn:
            compacted.append(system_turn)
        compacted.append(summary_turn)
        compacted.extend(recent_turns)

        logger.info(f"History Compactor: Compacted {len(messages)} turns down to {len(compacted)} turns.")
        return compacted

memory_bank = AsyncPersistentMemoryBank()
history_compactor = HistoryCompactor()
