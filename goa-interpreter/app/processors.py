from __future__ import annotations

from loguru import logger

from pipecat.frames.frames import Frame, InterimTranscriptionFrame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


class TranscriptionLogger(FrameProcessor):
    """Logs ASR frames as they flow through the pipeline. Used during bring-up.

    The frame is forwarded downstream unchanged.
    """

    def __init__(self, tag: str = "asr") -> None:
        super().__init__()
        self._tag = tag

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        if isinstance(frame, InterimTranscriptionFrame):
            logger.debug("[{}] interim: {}", self._tag, frame.text)
        elif isinstance(frame, TranscriptionFrame):
            logger.info("[{}] final  : {}", self._tag, frame.text)

        await self.push_frame(frame, direction)
