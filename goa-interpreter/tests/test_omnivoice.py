from __future__ import annotations

import io
import wave

import pytest

from app.omnivoice import _decode_wav_to_mono_pcm, _stereo_to_mono_s16le


def _make_wav(*, channels: int, sample_rate: int, samples: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(samples)
    return buf.getvalue()


def test_decode_mono_passthrough() -> None:
    samples = b"\x10\x00\x20\x00\x30\x00\x40\x00"
    wav = _make_wav(channels=1, sample_rate=24000, samples=samples)
    pcm, sr = _decode_wav_to_mono_pcm(wav)
    assert pcm == samples
    assert sr == 24000


def test_decode_stereo_downmix() -> None:
    # L=100, R=200 -> mono=150 (s16le)
    stereo = (100).to_bytes(2, "little", signed=True) + (200).to_bytes(2, "little", signed=True)
    wav = _make_wav(channels=2, sample_rate=22050, samples=stereo)
    pcm, sr = _decode_wav_to_mono_pcm(wav)
    assert sr == 22050
    val = int.from_bytes(pcm, "little", signed=True)
    assert val == 150


def test_stereo_downmix_clamps() -> None:
    # extreme values should not overflow int16
    stereo = (32767).to_bytes(2, "little", signed=True) + (32767).to_bytes(2, "little", signed=True)
    mono = _stereo_to_mono_s16le(stereo)
    assert int.from_bytes(mono, "little", signed=True) == 32767


def test_unsupported_sample_width_rejected() -> None:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(1)  # 8-bit, unsupported
        wf.setframerate(8000)
        wf.writeframes(b"\x80\x80\x80")
    with pytest.raises(ValueError):
        _decode_wav_to_mono_pcm(buf.getvalue())
