import os
import httpx
from dotenv import load_dotenv

load_dotenv()

NVIDIA_WHISPER_API_KEY = os.getenv("NVIDIA_WHISPER_API_KEY")
NVIDIA_WHISPER_MODEL = os.getenv("NVIDIA_WHISPER_MODEL", "whisper-large-v3")
NVIDIA_WHISPER_BASE_URL = os.getenv(
    "NVIDIA_WHISPER_BASE_URL",
    "https://ai.api.nvidia.com/v1/audio/transcriptions",
)


async def transcribe_audio(file_bytes: bytes, filename: str) -> str:
    """Send audio bytes to NVIDIA NIM Whisper endpoint and return the transcript."""
    headers = {
        "Authorization": f"Bearer {NVIDIA_WHISPER_API_KEY}",
    }

    files = {
        "file": (filename, file_bytes),
    }
    data = {
        "model": NVIDIA_WHISPER_MODEL,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            NVIDIA_WHISPER_BASE_URL,
            headers=headers,
            files=files,
            data=data,
            timeout=60.0,
        )

    if response.status_code >= 400:
        raise RuntimeError(
            f"NVIDIA Whisper API error ({response.status_code}): {response.text}"
        )

    result = response.json()
    return result.get("text", "").strip()
