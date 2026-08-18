from collections.abc import Callable
import re
import subprocess

from app.config import Settings


class LocalCpuTranslationAdapter:
    def __init__(self, command: str, model_path: str):
        self.command = command
        self.model_path = model_path

    def __call__(self, text: str) -> str:
        completed = subprocess.run(
            [self.command, "--model", self.model_path],
            input=text,
            text=True,
            capture_output=True,
            check=True,
            timeout=120,
        )
        translated = completed.stdout.strip()
        if not translated:
            raise RuntimeError("Local translation returned no text")
        return translated


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
            translate = self._translate
            if translate is None and self.settings.translation_configured:
                translate = LocalCpuTranslationAdapter(
                    self.settings.voc_translation_command,
                    self.settings.voc_translation_model_path,
                )
            if translate is None:
                result["status"] = "unavailable"
            else:
                result["translated_text"] = translate(text)
                result["status"] = "translated"
        return result
