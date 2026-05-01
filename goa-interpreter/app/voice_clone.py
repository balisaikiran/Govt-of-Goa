from __future__ import annotations

import httpx
from loguru import logger

ELEVENLABS_VOICES_ADD = "https://api.elevenlabs.io/v1/voices/add"


async def clone_voice(
    *,
    api_key: str,
    name: str,
    audio_bytes: bytes,
    audio_filename: str,
    audio_mime: str = "audio/wav",
    description: str | None = None,
) -> str:
    """Upload a voice sample to ElevenLabs Instant Voice Cloning. Returns voice_id."""
    files = {"files": (audio_filename, audio_bytes, audio_mime)}
    data: dict[str, str] = {"name": name}
    if description:
        data["description"] = description

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            ELEVENLABS_VOICES_ADD,
            headers={"xi-api-key": api_key},
            data=data,
            files=files,
        )
        resp.raise_for_status()
        body = resp.json()

    voice_id = body.get("voice_id")
    if not voice_id:
        raise RuntimeError(f"ElevenLabs IVC response missing voice_id: {body}")
    logger.info("voice cloned name={} voice_id={}", name, voice_id)
    return voice_id
