from datetime import timedelta

from livekit.api import AccessToken, VideoGrants

from app.config import Settings


def master_token(settings: Settings, room: str, identity: str) -> str:
    grants = VideoGrants(
        room_join=True,
        room=room,
        can_publish=True,
        can_subscribe=False,
        can_publish_data=False,
    )
    return (
        AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(grants)
        .with_ttl(timedelta(hours=4))
        .to_jwt()
    )


def listener_token(settings: Settings, room: str, identity: str) -> str:
    grants = VideoGrants(
        room_join=True,
        room=room,
        can_publish=False,
        can_subscribe=True,
        can_publish_data=False,
    )
    return (
        AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(grants)
        .with_ttl(timedelta(hours=4))
        .to_jwt()
    )


def agent_token(settings: Settings, room: str, identity: str, can_publish: bool) -> str:
    """Token for the Pipecat agent — subscribes to master audio in master rooms,
    publishes synthesised audio in per-language rooms."""
    grants = VideoGrants(
        room_join=True,
        room=room,
        can_publish=can_publish,
        can_subscribe=not can_publish,
        can_publish_data=False,
        hidden=True,
    )
    return (
        AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_kind("agent")
        .with_grants(grants)
        .with_ttl(timedelta(hours=4))
        .to_jwt()
    )
