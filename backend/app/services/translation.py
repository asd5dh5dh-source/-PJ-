from collections.abc import Callable
import re

from app.config import Settings


class TranslationService:
    def __init__(
        self,
        settings: Settings,
        translate: Callable[[str], str] | None = None,
    ):
        self.settings = settings
        self._translate = translate

    def translate(self, text: str) -> dict[str, str | None]:
        result = {
            "source_text": text,
            "translated_text": None,
            "status": "preview",
        }
        if re.search(r"[가-힣]", text):
            result["status"] = "bypassed"
        elif self.settings.runtime_profile == "internal":
            if self._translate is None:
                result["status"] = "unavailable"
            else:
                result["translated_text"] = self._translate(text)
                result["status"] = "translated"
        return result
