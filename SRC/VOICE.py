"""Voice layer: optional text-to-speech and speech-to-text.

Both are strictly optional.  The prototype must never break because a laptop
has no microphone or the optional packages are missing — every entry point
returns a status tuple instead of raising, and the UI shows an honest message.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def tts_available() -> bool:
    try:
        import pyttsx3  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


def stt_available() -> bool:
    try:
        import speech_recognition  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


def speak(text: str, lang: str = "en") -> Tuple[bool, str]:
    """Speak ``text`` locally (offline SAPI5 on Windows).  Never raises."""
    if not text:
        return False, "empty text"
    if not tts_available():
        return False, "pyttsx3 not installed (optional)"
    try:  # pragma: no cover - hardware dependent
        import pyttsx3

        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        chosen = None
        for voice in voices:
            languages = []
            try:
                languages = [str(x).lower() for x in getattr(voice, "languages", [])]
            except Exception:  # noqa: BLE001
                pass
            blob = " ".join(languages) + " " + str(getattr(voice, "id", "")).lower()
            if lang == "ta" and ("ta" in blob or "tamil" in blob or "india" in blob):
                chosen = voice.id
                break
        if chosen:
            engine.setProperty("voice", chosen)
        engine.setProperty("rate", 150)
        engine.say(text)
        engine.runAndWait()
        try:
            engine.stop()
        except Exception:  # noqa: BLE001
            pass
        return True, "spoken"
    except Exception as exc:  # noqa: BLE001
        return False, f"speech failed: {type(exc).__name__}"


def listen(lang: str = "en", timeout: int = 6) -> Tuple[bool, str]:
    """Listen on the microphone and transcribe.  Never raises.

    Returns ``(ok, text_or_reason)``.  Uses the Google STT endpoint, so it
    needs internet; the demo always offers a typed alternative.
    """
    if not stt_available():
        return False, "SpeechRecognition not installed (optional)"
    try:  # pragma: no cover - hardware dependent
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.4)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=12)
        code = "ta-IN" if lang == "ta" else "en-IN"
        text = recognizer.recognize_google(audio, language=code)
        return True, text
    except TypeError as exc:
        return False, f"microphone error: {exc}"
    except Exception as exc:  # noqa: BLE001
        return False, f"could not transcribe ({type(exc).__name__}) — please type instead"
