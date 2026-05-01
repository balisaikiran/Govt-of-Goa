from __future__ import annotations

import secrets
from dataclasses import dataclass, field


@dataclass
class Session:
    id: str
    source_language: str
    target_languages: list[str]
    voice_id: str

    @property
    def master_room(self) -> str:
        return f"session-{self.id}-master"

    def listener_room(self, lang: str) -> str:
        return f"session-{self.id}-{lang}"

    def all_listener_rooms(self) -> dict[str, str]:
        return {lang: self.listener_room(lang) for lang in self.target_languages}


@dataclass
class SessionRegistry:
    _by_id: dict[str, Session] = field(default_factory=dict)

    def create(
        self, source_language: str, target_languages: list[str], voice_id: str
    ) -> Session:
        sid = secrets.token_urlsafe(6)
        session = Session(
            id=sid,
            source_language=source_language,
            target_languages=target_languages,
            voice_id=voice_id,
        )
        self._by_id[sid] = session
        return session

    def get(self, sid: str) -> Session | None:
        return self._by_id.get(sid)

    def remove(self, sid: str) -> None:
        self._by_id.pop(sid, None)


registry = SessionRegistry()
