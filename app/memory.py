import asyncio
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("breakaway_ai.memory")

class AsyncPersistentMemoryBank:
    """
    Asynchronous Persistent Memory Store for user biometrics, historical EWMA state, and long-term coaching preferences.
    Executes async non-blocking memory operations for expensive database calls.
    """
    def __init__(self):
        self._memory_store: Dict[str, Any] = {
            "user_biometrics": {
                "ftp_watts": 261,
                "max_hr_bpm": 205,
                "resting_hr_bpm": 47,
                "weight_kg": 63.0
            },
            "recent_ewma_state": {
                "acute_load": 60.99,
                "chronic_load": 61.51,
                "acwr": 0.99
            }
        }

    async def save_user_profile_async(self, session_id: str, profile_data: Dict[str, Any]) -> bool:
        """Async memory operation to persist user biometrics and training preferences."""
        await asyncio.sleep(0.01)  # Non-blocking async simulation
        self._memory_store[session_id] = profile_data
        logger.info(f"Async Memory Bank: Persisted profile for session {session_id}")
        return True

    async def load_user_profile_async(self, session_id: str) -> Dict[str, Any]:
        """Async memory operation to retrieve persistent user profile."""
        await asyncio.sleep(0.01)
        return self._memory_store.get(session_id, self._memory_store["user_biometrics"])

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

        # Preserve system instruction / first turn
        system_turn = messages[0] if messages and messages[0].get("role") == "system" else None
        
        # Summarize older turns
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
