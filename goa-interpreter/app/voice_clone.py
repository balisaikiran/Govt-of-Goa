from __future__ import annotations

import re
from pathlib import Path

import httpx
from loguru import logger

ELEVENLABS_VOICES_ADD = "https://api.elevenlabs.io/v1/voices/add"


async def clone_voice_elevenlabs(
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
    logger.info("voice cloned (elevenlabs) name={} voice_id={}", name, voice_id)
    return voice_id


_SAFE = re.compile(r"[^a-zA-Z0-9_-]")


async def clone_voice_omnivoice(
    *,
    voices_dir: str,
    name: str,
    audio_bytes: bytes,
    audio_filename: str,
) -> str:
    """Save the voice sample to the OmniVoice voices directory and return the
    filename stem to use as the `sample` field in OmniVoice /tts requests.
    The voices directory is expected to be mounted into the OmniVoice-local
    container as its sample directory.
    """
    suffix = Path(audio_filename).suffix or ".wav"
    safe_name = _SAFE.sub("_", name) or "voice"
    voice_id = f"{safe_name}-{abs(hash(audio_bytes)) % 10**8:08d}"

    out_dir = Path(voices_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{voice_id}{suffix}"
    out_path.write_bytes(audio_bytes)

    logger.info("voice cloned (omnivoice) name={} -> {}", name, out_path)
    return voice_id
