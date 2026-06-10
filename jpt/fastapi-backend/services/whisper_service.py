"""Audio transcription via Google Gemini Flash.

Gemini 1.5/2.0 Flash natively understands audio and supports multilingual
transcription including Nepali, which makes it a much better fit than
Whisper for non-English inventory commands.
"""
from __future__ import annotations

import base64
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Use the free flash model — swap to "gemini-1.5-pro" for higher accuracy if needed
GEMINI_MODEL = os.getenv("GEMINI_TRANSCRIPTION_MODEL", "gemini-2.0-flash")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


async def transcribe_audio(file_bytes: bytes, filename: str) -> str:
    """Transcribe audio bytes using Gemini Flash's native audio understanding.

    Supports Nepali, English, and other languages automatically.
    Returns the plain-text transcript.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Get a free key at https://aistudio.google.com/apikey"
        )

    # Detect MIME type from filename extension
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "webm"
    mime_map = {
        "mp3": "audio/mpeg",
        "mp4": "audio/mp4",
        "m4a": "audio/mp4",
        "wav": "audio/wav",
        "webm": "audio/webm",
        "ogg": "audio/ogg",
        "flac": "audio/flac",
        "aac": "audio/aac",
    }
    mime_type = mime_map.get(ext, "audio/mpeg")

    # Encode audio as base64 for the inline data API
    audio_b64 = base64.b64encode(file_bytes).decode("utf-8")

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": audio_b64,
                        }
                    },
                    {
                        "text": (
                            "Transcribe this audio exactly as spoken. "
                            "The audio may be in Nepali, English, or a mix of both. "
                            "Output only the transcription text — no commentary, "
                            "no timestamps, no labels."
                        )
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0,
        },
    }

    url = f"{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload)

    if response.status_code >= 400:
        raise RuntimeError(
            f"Gemini API error ({response.status_code}): {response.text}"
        )

    result = response.json()

    try:
        transcript = result["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError) as exc:
        raise RuntimeError(
            f"Unexpected Gemini response shape: {result}"
        ) from exc

    return transcript
