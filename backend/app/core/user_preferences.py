"""Gnosis User Preferences — Per-user conversation and display settings."""

import logging
from dataclasses import dataclass
from typing import Dict

logger = logging.getLogger("gnosis.preferences")


@dataclass
class UserPreferences:
    user_id: str = ""
    preferred_language: str = "en"
    response_length: str = "medium"  # short/medium/long
    code_style: str = "commented"  # commented/minimal/verbose
    timezone: str = "UTC"
    notifications_enabled: bool = True


class UserPreferencesEngine:
    VALID_LENGTHS = {"short", "medium", "long"}
    VALID_CODE_STYLES = {"commented", "minimal", "verbose"}

    def __init__(self):
        self._prefs: Dict[str, UserPreferences] = {}

    def get_preferences(self, user_id: str) -> UserPreferences:
        if user_id not in self._prefs:
            self._prefs[user_id] = UserPreferences(user_id=user_id)
        return self._prefs[user_id]

    def set_preferences(self, user_id: str, **kwargs) -> UserPreferences:
        if (
            "response_length" in kwargs
            and kwargs["response_length"] not in self.VALID_LENGTHS
        ):
            raise ValueError(
                f"Invalid response_length. Must be one of {self.VALID_LENGTHS}"
            )
        if (
            "code_style" in kwargs
            and kwargs["code_style"] not in self.VALID_CODE_STYLES
        ):
            raise ValueError(
                f"Invalid code_style. Must be one of {self.VALID_CODE_STYLES}"
            )
        prefs = self.get_preferences(user_id)
        for k, v in kwargs.items():
            if hasattr(prefs, k) and k != "user_id":
                setattr(prefs, k, v)
        logger.info(f"Updated preferences for user {user_id}")
        return prefs

    def update_preferences(self, user_id: str, **kwargs) -> UserPreferences:
        return self.set_preferences(user_id, **kwargs)

    def reset_preferences(self, user_id: str) -> UserPreferences:
        self._prefs[user_id] = UserPreferences(user_id=user_id)
        return self._prefs[user_id]


user_preferences_engine = UserPreferencesEngine()
