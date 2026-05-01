from __future__ import annotations

from dataclasses import dataclass

import pytest

from pipecat.frames.frames import (
    InterimTranscriptionFrame,
    TextFrame,
    TranscriptionFrame,
)
from pipecat.tests.utils import run_test

from app.orchestrator import StablePhraseBuffer


@dataclass
class _FakeResult:
    speech_final: bool = False


def _final(text: str, speech_final: bool = False) -> TranscriptionFrame:
    return TranscriptionFrame(
        text=text,
        user_id="u",
        timestamp="2026-05-01T00:00:00Z",
        language=None,
        result=_FakeResult(speech_final=speech_final),
    )


def _interim(text: str) -> InterimTranscriptionFrame:
    return InterimTranscriptionFrame(
        text=text,
        user_id="u",
        timestamp="2026-05-01T00:00:00Z",
        language=None,
        result=_FakeResult(),
    )


@pytest.mark.asyncio
async def test_drops_interim_only() -> None:
    received_down, _ = await run_test(
        StablePhraseBuffer(),
        frames_to_send=[_interim("hel"), _interim("hello"), _interim("hello wo")],
        expected_down_frames=[],
    )
    text_frames = [f for f in received_down if isinstance(f, TextFrame)]
    assert text_frames == []


@pytest.mark.asyncio
async def test_flush_on_speech_final() -> None:
    received_down, _ = await run_test(
        StablePhraseBuffer(),
        frames_to_send=[
            _interim("hel"),
            _final("hello"),
            _final("world", speech_final=True),
        ],
        expected_down_frames=[TextFrame],
    )
    texts = [f.text for f in received_down if isinstance(f, TextFrame)]
    assert texts == ["hello world"]


@pytest.mark.asyncio
async def test_flush_on_terminal_punctuation() -> None:
    received_down, _ = await run_test(
        StablePhraseBuffer(),
        frames_to_send=[_final("Good morning"), _final("everyone.")],
        expected_down_frames=[TextFrame],
    )
    texts = [f.text for f in received_down if isinstance(f, TextFrame)]
    assert texts == ["Good morning everyone."]


@pytest.mark.asyncio
async def test_two_phrases_emit_separately() -> None:
    received_down, _ = await run_test(
        StablePhraseBuffer(),
        frames_to_send=[
            _final("Welcome."),
            _final("How are you", speech_final=False),
            _final("today?"),
        ],
        expected_down_frames=[TextFrame, TextFrame],
    )
    texts = [f.text for f in received_down if isinstance(f, TextFrame)]
    assert texts == ["Welcome.", "How are you today?"]
