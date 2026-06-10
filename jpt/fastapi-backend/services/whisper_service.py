"""Audio transcription via Azure AI Speech Service.

Converts input audio dynamically to 16kHz WAV format (required by Azure REST API)
using FFmpeg, then transcribes it using Azure Speech REST API.
"""
from __future__ import annotations

import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", "")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "koreacentral")
AZURE_SPEECH_LANGUAGE = os.getenv("AZURE_SPEECH_LANGUAGE", "ne-NP")


async def convert_to_wav_16k(file_bytes: bytes) -> bytes:
    """Convert input audio (mp3, webm, etc.) to 16kHz WAV PCM 16-bit mono using ffmpeg in-memory."""
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-i", "pipe:0",
        "-f", "wav",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        "pipe:1",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate(input=file_bytes)
    if process.returncode != 0:
        raise RuntimeError(
            f"FFmpeg audio conversion failed: {stderr.decode()}"
        )
    return stdout


async def transcribe_audio(file_bytes: bytes, filename: str, language: str | None = None) -> str:
    """Transcribe audio bytes using Azure AI Speech REST API.

    Automatically converts audio format to WAV PCM 16kHz mono.
    """
    if not AZURE_SPEECH_KEY:
        raise RuntimeError(
            "AZURE_SPEECH_KEY is not set in environment variables."
        )

    # Convert audio to wav first
    wav_bytes = await convert_to_wav_16k(file_bytes)

    lang = language or AZURE_SPEECH_LANGUAGE

    url = f"https://{AZURE_SPEECH_REGION}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language={lang}"

    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_SPEECH_KEY,
        "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, content=wav_bytes, timeout=30.0)

    if response.status_code >= 400:
        raise RuntimeError(
            f"Azure Speech API error ({response.status_code}): {response.text}"
        )

    result = response.json()
    status = result.get("RecognitionStatus")
    if status == "Success":
        return result.get("DisplayText", "").strip()
    elif status == "NoMatch":
        return ""
    else:
        raise RuntimeError(f"Azure Speech recognition failed with status: {status}. Response: {result}")
