from __future__ import annotations

from loguru import logger
from openai import AsyncOpenAI

from pipecat.frames.frames import Frame, TextFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

LANGUAGE_NAMES = {
    "hi": "Hindi",
    "es": "Spanish",
    "en": "English",
    "fr": "French",
    "de": "German",
    "ja": "Japanese",
    "ko": "Korean",
    "pt": "Portuguese",
    "ar": "Arabic",
    "ta": "Tamil",
    "bn": "Bengali",
    "mr": "Marathi",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "ur": "Urdu",
}


def _name(code: str) -> str:
    return LANGUAGE_NAMES.get(code, code)


class TranslateProcessor(FrameProcessor):
    """Translates each incoming TextFrame from source_language to target_language
    using an OpenAI chat model. Emits a TextFrame downstream with the translation.

    Non-TextFrames pass through untouched.
    """

    def __init__(
        self,
        *,
        api_key: str,
        source_language: str,
        target_language: str,
        model: str = "gpt-4o-mini",
    ) -> None:
        super().__init__()
        self._client = AsyncOpenAI(api_key=api_key)
        self._source = source_language
        self._target = target_language
        self._model = model
        self._system = (
            f"You are a professional simultaneous interpreter translating spoken "
            f"{_name(source_language)} into {_name(target_language)}. "
            "Output ONLY the translated sentence, with no preamble, no quotes, "
            "no explanations. Preserve tone, register, and named entities. "
            "If the input is already in the target language, repeat it verbatim."
        )

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        if isinstance(frame, TextFrame) and frame.text.strip():
            translated = await self._translate(frame.text)
            await self.push_frame(TextFrame(translated), direction)
            return

        await self.push_frame(frame, direction)

    async def _translate(self, text: str) -> str:
        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": self._system},
                    {"role": "user", "content": text},
                ],
                temperature=0.2,
                max_tokens=400,
            )
            out = (resp.choices[0].message.content or "").strip()
            logger.info("[{}→{}] {} ⇒ {}", self._source, self._target, text, out)
            return out or text
        except Exception:
            logger.exception("translation failed; falling back to source text")
            return text
