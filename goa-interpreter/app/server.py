from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pydantic import BaseModel, Field

from app.config import get_settings
from app.livekit_tokens import listener_token, master_token
from app.runner import manager
from app.sessions import registry
from app.voice_clone import clone_voice_elevenlabs, clone_voice_omnivoice

app = FastAPI(title="Goa Interpreter")
app.mount("/clients", StaticFiles(directory="clients"), name="clients")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse("clients/index.html")


class VoiceCloneResponse(BaseModel):
    voice_id: str
    provider: str


@app.post("/voice/clone", response_model=VoiceCloneResponse)
async def voice_clone(
    name: str = Form(...),
    sample: UploadFile = File(...),
    provider: str = Form("elevenlabs"),
) -> VoiceCloneResponse:
    settings = get_settings()
    audio_bytes = await sample.read()
    if len(audio_bytes) < 1024:
        raise HTTPException(400, "audio sample too small")

    provider = provider.lower()
    if provider == "omnivoice":
        voice_id = await clone_voice_omnivoice(
            voices_dir=settings.voices_dir,
            name=name,
            audio_bytes=audio_bytes,
            audio_filename=sample.filename or "sample.wav",
        )
    elif provider == "elevenlabs":
        voice_id = await clone_voice_elevenlabs(
            api_key=settings.elevenlabs_api_key,
            name=name,
            audio_bytes=audio_bytes,
            audio_filename=sample.filename or "sample.webm",
            audio_mime=sample.content_type or "audio/webm",
        )
    else:
        raise HTTPException(400, f"unknown provider {provider!r}")
    return VoiceCloneResponse(voice_id=voice_id, provider=provider)


class StartSessionRequest(BaseModel):
    target_languages: list[str] = Field(..., min_length=1, examples=[["hi", "es"]])
    voice_id: str | None = None
    source_language: str | None = None
    tts_provider: str | None = None  # "elevenlabs" | "omnivoice"


class StartSessionResponse(BaseModel):
    session_id: str
    livekit_url: str
    tts_provider: str
    master: dict
    listeners: dict[str, dict]


@app.post("/session/start", response_model=StartSessionResponse)
async def start_session(req: StartSessionRequest) -> StartSessionResponse:
    settings = get_settings()
    tts_provider = (req.tts_provider or settings.default_tts_provider).lower()
    if tts_provider not in {"elevenlabs", "omnivoice"}:
        raise HTTPException(400, f"unknown tts_provider {tts_provider!r}")

    voice_id = req.voice_id or (
        settings.elevenlabs_default_voice_id if tts_provider == "elevenlabs" else ""
    )
    if tts_provider == "omnivoice" and not voice_id:
        raise HTTPException(
            400,
            "OmniVoice has no default voice — call /voice/clone first with provider=omnivoice",
        )

    source = req.source_language or settings.source_language

    session = registry.create(
        source_language=source,
        target_languages=req.target_languages,
        voice_id=voice_id,
        tts_provider=tts_provider,
    )

    master = {
        "room": session.master_room,
        "token": master_token(settings, session.master_room, identity="master"),
    }
    listeners = {
        lang: {
            "room": session.listener_room(lang),
            "token": listener_token(
                settings, session.listener_room(lang), identity=f"listener-{lang}"
            ),
        }
        for lang in session.target_languages
    }

    logger.info(
        "session.started id={} source={} targets={} tts={} voice_id={}",
        session.id, session.source_language, session.target_languages,
        session.tts_provider, session.voice_id,
    )
    await manager.start(settings, session)
    return StartSessionResponse(
        session_id=session.id,
        livekit_url=settings.livekit_url,
        tts_provider=session.tts_provider,
        master=master,
        listeners=listeners,
    )


@app.post("/session/{session_id}/stop")
async def stop_session(session_id: str) -> dict[str, str]:
    if not registry.get(session_id):
        raise HTTPException(404, "session not found")
    await manager.stop(session_id)
    registry.remove(session_id)
    return {"status": "stopped", "session_id": session_id}


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.server:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
