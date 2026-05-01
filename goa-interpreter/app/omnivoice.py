from __future__ import annotations

import io
import wave
from collections.abc import AsyncGenerator

import httpx
from loguru import logger

from pipecat.frames.frames import Frame, TTSAudioRawFrame
from pipecat.services.tts_service import TTSService
from pipecat.transcriptions.language import Language

DEFAULT_SAMPLE_RATE = 24000


class OmniVoiceTTSService(TTSService):
    """Pipecat TTS service backed by an OmniVoice-local HTTP server.

    OmniVoice (k2-fsa) is an open-source 600+ language zero-shot voice-cloning
    model. The wrapper at github.com/pasadei/OmniVoice-local exposes a REST
    API on port 8000:

        POST /tts  { text, sample, output_format, ... }  -> raw audio bytes

    OmniVoice has no native streaming, but ~40x realtime inference makes
    full-utterance synthesis of a sentence fast enough (~100-300 ms).
    """

    def __init__(
        self,
        *,
        base_url: str,
        voice_sample: str,
        language: Language | None = None,
        speed: float = 1.0,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        request_timeout: float = 30.0,
        chunk_bytes: int = 4096,
        **kwargs,
    ) -> None:
        super().__init__(sample_rate=sample_rate, **kwargs)
        self._base_url = base_url.rstrip("/")
        self._voice_sample = voice_sample
        self._language = language
        self._speed = speed
        self._timeout = request_timeout
        self._chunk_bytes = chunk_bytes

    async def run_tts(
        self, text: str, context_id: str
    ) -> AsyncGenerator[Frame | None, None]:
        text = (text or "").strip()
        if not text:
            return

        body: dict = {
            "text": text,
            "sample": self._voice_sample,
            "speed": self._speed,
            "output_format": "wav",
        }
        if self._language:
            body["language"] = self._language.value

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(f"{self._base_url}/tts", json=body)
                resp.raise_for_status()
                audio_bytes = resp.content
        except Exception:
            logger.exception("OmniVoice synthesis failed for {!r}", text[:60])
            return

        try:
            pcm, sr = _decode_wav_to_mono_pcm(audio_bytes)
        except Exception:
            logger.exception("OmniVoice returned audio that failed to parse as WAV")
            return

        for i in range(0, len(pcm), self._chunk_bytes):
            chunk = pcm[i : i + self._chunk_bytes]
            if not chunk:
                break
            yield TTSAudioRawFrame(audio=chunk, sample_rate=sr, num_channels=1)


def _decode_wav_to_mono_pcm(wav_bytes: bytes) -> tuple[bytes, int]:
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        sr = wf.getframerate()
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        pcm = wf.readframes(wf.getnframes())

    if sampwidth != 2:
        raise ValueError(f"unsupported sample width {sampwidth} (need 16-bit)")
    if channels == 1:
        return pcm, sr
    if channels == 2:
        return _stereo_to_mono_s16le(pcm), sr
    raise ValueError(f"unsupported channel count {channels}")


def _stereo_to_mono_s16le(pcm: bytes) -> bytes:
    import array

    stereo = array.array("h", pcm)
    mono = array.array("h", [0] * (len(stereo) // 2))
    for i in range(0, len(stereo), 2):
        # average L + R, clamp to int16 range
        v = (stereo[i] + stereo[i + 1]) // 2
        mono[i // 2] = max(-32768, min(32767, v))
    return mono.tobytes()
