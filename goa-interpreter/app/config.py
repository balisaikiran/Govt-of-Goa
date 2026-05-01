from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    livekit_url: str = "ws://localhost:7880"
    livekit_api_key: str
    livekit_api_secret: str

    deepgram_api_key: str
    openai_api_key: str
    elevenlabs_api_key: str

    translation_model: str = "gpt-4o-mini"
    elevenlabs_default_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    elevenlabs_model: str = "eleven_multilingual_v2"

    # OmniVoice (self-hosted via OmniVoice-local). Empty disables OmniVoice.
    omnivoice_url: str = "http://localhost:8000"
    voices_dir: str = "voices"
    default_tts_provider: str = "elevenlabs"  # elevenlabs | omnivoice

    source_language: str = "en"

    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
