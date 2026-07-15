"""
User data persistence for 4 Pics 1 Word.
All progress, scores, settings, and API key are stored in a single JSON file
located in Kivy's user_data_dir (private to the app on Android/iOS, and in
the user's home directory on desktop).

Hint economy
------------
Hints are no longer free. Each hint costs HINT_COST points deducted from
the player's score. Points are earned by solving words (100 x level each).
"""

import os
import json
from datetime import datetime

# Points required to use one hint
HINT_COST: int = 100


class UserData:
    """Loads and saves player progress to disk as JSON."""

    def __init__(self, data_dir: str):
        os.makedirs(data_dir, exist_ok=True)
        self._filepath = os.path.join(data_dir, "user_data.json")
        self.data = self._load()

    # ── internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _defaults() -> dict:
        return {
            "username":        "Player",
            "score":           0,
            "high_score":      0,
            "level":           1,
            "completed_words": [],   # list of lowercase word strings
            "total_games":     0,
            "correct_answers": 0,
            "api_key":         "",
            "created_at":      datetime.now().isoformat(),
            "last_played":     None,
        }

    def _load(self) -> dict:
        defaults = self._defaults()
        if os.path.exists(self._filepath):
            try:
                with open(self._filepath, "r", encoding="utf-8") as fh:
                    saved = json.load(fh)
                # Overlay saved values; new default keys are preserved.
                defaults.update(saved)
            except (json.JSONDecodeError, IOError, ValueError):
                pass  # Corrupted file → start fresh
        return defaults

    # ── public: persistence ───────────────────────────────────────────────────

    def save(self) -> None:
        """Write current data to disk."""
        self.data["last_played"] = datetime.now().isoformat()
        try:
            with open(self._filepath, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, indent=2, ensure_ascii=False)
        except IOError as exc:
            print(f"[UserData] Could not save: {exc}")

    # ── public: properties ────────────────────────────────────────────────────

    @property
    def username(self) -> str:
        return self.data.get("username", "Player")

    @username.setter
    def username(self, value: str) -> None:
        self.data["username"] = value
        self.save()

    @property
    def score(self) -> int:
        return self.data.get("score", 0)

    @property
    def high_score(self) -> int:
        return self.data.get("high_score", 0)

    @property
    def level(self) -> int:
        return self.data.get("level", 1)

    @property
    def api_key(self) -> str:
        return self.data.get("api_key", "")

    @api_key.setter
    def api_key(self, value: str) -> None:
        self.data["api_key"] = value
        self.save()

    # ── public: game actions ──────────────────────────────────────────────────

    def start_game(self) -> None:
        """Call once when the user begins a new game session."""
        self.data["total_games"] = self.data.get("total_games", 0) + 1
        self.save()

    def add_score(self, points: int) -> None:
        """Add points and update high-score if beaten."""
        self.data["score"] = self.data.get("score", 0) + points
        if self.data["score"] > self.data.get("high_score", 0):
            self.data["high_score"] = self.data["score"]
        self.save()

    def complete_word(self, word: str) -> None:
        """Record a correctly guessed word, update level and hint bonus."""
        word = word.lower()
        completed: list = self.data.get("completed_words", [])
        if word not in completed:
            completed.append(word)
            self.data["completed_words"] = completed

        self.data["correct_answers"] = self.data.get("correct_answers", 0) + 1

        # Level up every 5 completed words
        self.data["level"] = len(completed) // 5 + 1

        self.save()

    def use_hint(self) -> bool:
        """Spend HINT_COST points to reveal one letter.
        Returns True on success, False if the player cannot afford it."""
        if self.data.get("score", 0) >= HINT_COST:
            self.data["score"] -= HINT_COST
            self.save()
            return True
        return False

    def reset_progress(self) -> None:
        """Clear completed words and reset score/level (keeps API key & name)."""
        self.data["completed_words"] = []
        self.data["score"]           = 0
        self.data["level"]           = 1
        self.data["correct_answers"] = 0
        self.save()
