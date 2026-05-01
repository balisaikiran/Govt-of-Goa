from __future__ import annotations

from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.parallel_pipeline import ParallelPipeline
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.audio.vad_processor import VADProcessor
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.transcriptions.language import Language
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.livekit.transport import LiveKitTransport

from app.config import Settings
from app.livekit_tokens import agent_token
from app.orchestrator import StablePhraseBuffer
from app.processors import TranscriptionLogger
from app.sessions import Session
from app.translator import TranslateProcessor

INPUT_SAMPLE_RATE = 16000
OUTPUT_SAMPLE_RATE = 24000  # ElevenLabs default for streaming


def _language(code: str) -> Language | None:
    try:
        return Language(code)
    except ValueError:
        logger.warning("unknown language code {} — passing raw to TTS", code)
        return None


def _master_input_transport(settings: Settings, session: Session) -> LiveKitTransport:
    token = agent_token(
        settings,
        room=session.master_room,
        identity=f"agent-{session.id}-asr",
        can_publish=False,
    )
    params = TransportParams(
        audio_in_enabled=True,
        audio_in_sample_rate=INPUT_SAMPLE_RATE,
        audio_in_passthrough=True,
        audio_out_enabled=False,
    )
    return LiveKitTransport(
        url=settings.livekit_url,
        token=token,
        room_name=session.master_room,
        params=params,
        input_name=f"master-input-{session.id}",
    )


def _language_output_transport(
    settings: Settings, session: Session, lang: str
) -> LiveKitTransport:
    room = session.listener_room(lang)
    token = agent_token(
        settings,
        room=room,
        identity=f"agent-{session.id}-tts-{lang}",
        can_publish=True,
    )
    params = TransportParams(
        audio_in_enabled=False,
        audio_out_enabled=True,
        audio_out_sample_rate=OUTPUT_SAMPLE_RATE,
    )
    return LiveKitTransport(
        url=settings.livekit_url,
        token=token,
        room_name=room,
        params=params,
        output_name=f"out-{session.id}-{lang}",
    )


def _stt_service(settings: Settings, source_language: str) -> DeepgramSTTService:
    return DeepgramSTTService(
        api_key=settings.deepgram_api_key,
        settings=DeepgramSTTService.Settings(
            model="nova-3-general",
            language=source_language,
            interim_results=True,
            punctuate=True,
            smart_format=True,
        ),
    )


def _tts_service(settings: Settings, target_language: str, voice_id: str) -> ElevenLabsTTSService:
    return ElevenLabsTTSService(
        api_key=settings.elevenlabs_api_key,
        settings=ElevenLabsTTSService.Settings(
            voice=voice_id,
            model=settings.elevenlabs_model,
            language=_language(target_language),
        ),
        sample_rate=OUTPUT_SAMPLE_RATE,
    )


def _language_branch(
    settings: Settings, session: Session, lang: str
) -> tuple[list, LiveKitTransport]:
    """A single branch: translate → TTS → publish to that language's room."""
    out_transport = _language_output_transport(settings, session, lang)
    branch = [
        TranslateProcessor(
            api_key=settings.openai_api_key,
            source_language=session.source_language,
            target_language=lang,
            model=settings.translation_model,
        ),
        _tts_service(settings, lang, session.voice_id),
        out_transport.output(),
    ]
    return branch, out_transport


def build_pipeline_task(settings: Settings, session: Session) -> PipelineTask:
    """Master room → VAD → STT → orchestrator → ParallelPipeline (one branch per
    target language: translate → TTS → publish to that language's room).
    """
    master_transport = _master_input_transport(settings, session)
    vad = VADProcessor(vad_analyzer=SileroVADAnalyzer(sample_rate=INPUT_SAMPLE_RATE))
    stt = _stt_service(settings, session.source_language)
    asr_logger = TranscriptionLogger(tag=f"sess={session.id}")
    orchestrator = StablePhraseBuffer()

    branches = []
    out_transports: list[LiveKitTransport] = []
    for lang in session.target_languages:
        branch, out_transport = _language_branch(settings, session, lang)
        branches.append(branch)
        out_transports.append(out_transport)

    if len(branches) == 1:
        tail = branches[0]
    else:
        tail = [ParallelPipeline(*branches)]

    pipeline = Pipeline(
        [
            master_transport.input(),
            vad,
            stt,
            asr_logger,
            orchestrator,
            *tail,
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=INPUT_SAMPLE_RATE,
            audio_out_sample_rate=OUTPUT_SAMPLE_RATE,
            allow_interruptions=False,
        ),
    )

    @master_transport.event_handler("on_first_participant_joined")
    async def _on_first_joined(_t, participant_id: str) -> None:
        logger.info("session={} master joined: {}", session.id, participant_id)

    @master_transport.event_handler("on_participant_disconnected")
    async def _on_master_left(_t, participant_id: str) -> None:
        logger.info(
            "session={} master left: {} — stopping pipeline",
            session.id, participant_id,
        )
        await task.cancel()

    return task
