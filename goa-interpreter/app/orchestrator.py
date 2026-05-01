from __future__ import annotations

import asyncio

from loguru import logger

from pipecat.frames.frames import (
    Frame,
    InterimTranscriptionFrame,
    TextFrame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

TERMINAL_PUNCTUATION = (".", "?", "!", "।", "॥", "।।", "؟")


class StablePhraseBuffer(FrameProcessor):
    """Coalesces Deepgram fragments into one TextFrame per stable phrase.

    Deepgram emits a TranscriptionFrame for each ``is_final`` chunk, plus a
    flood of InterimTranscriptionFrames. A single sentence can span several
    final chunks before the model fires endpointing. Translating each chunk
    independently produces choppy, stuttering TTS, so we buffer here.

    Flush triggers:
    - ``speech_final`` from Deepgram (VAD-based endpointing fired) — strongest
    - Trailing terminal punctuation in a final chunk (``.?!`` etc.)
    - ``max_buffer_secs`` elapsed since first chunk in the current phrase
      (latency cap)

    Interim frames are dropped — they only exist to drive UI in the master
    client, never to feed translation.
    """

    def __init__(self, *, max_buffer_secs: float = 4.0) -> None:
        super().__init__()
        self._max_buffer_secs = max_buffer_secs
        self._buffer: list[str] = []
        self._language: object | None = None
        self._flush_task: asyncio.Task | None = None

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        if isinstance(frame, InterimTranscriptionFrame):
            return  # swallow

        if isinstance(frame, TranscriptionFrame):
            await self._handle_final(frame)
            return

        await self.push_frame(frame, direction)

    async def _handle_final(self, frame: TranscriptionFrame) -> None:
        text = (frame.text or "").strip()
        if not text:
            return

        self._buffer.append(text)
        self._language = frame.language or self._language
        speech_final = bool(getattr(frame.result, "speech_final", False))

        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._scheduled_flush())

        if speech_final or text.endswith(TERMINAL_PUNCTUATION):
            await self._flush(reason="speech_final" if speech_final else "punctuation")

    async def _scheduled_flush(self) -> None:
        try:
            await asyncio.sleep(self._max_buffer_secs)
            if self._buffer:
                await self._flush(reason="timeout")
        except asyncio.CancelledError:
            pass

    async def _flush(self, *, reason: str) -> None:
        if not self._buffer:
            return
        phrase = " ".join(self._buffer).strip()
        self._buffer.clear()
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
        self._flush_task = None
        logger.info("phrase ({}): {}", reason, phrase)
        await self.push_frame(TextFrame(phrase), FrameDirection.DOWNSTREAM)

    async def cleanup(self) -> None:
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
        await super().cleanup()
