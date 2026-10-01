from __future__ import annotations

import sys
from types import SimpleNamespace

from config import Settings
from services.livekit_service import LiveKitService


async def test_livekit_uses_mocked_api(monkeypatch: object) -> None:
    requests: list[object] = []

    class Room:
        async def create_room(self, request: object) -> None:
            requests.append(request)

        async def delete_room(self, request: object) -> None:
            requests.append(request)

    class Client:
        def __init__(self, _: str) -> None:
            self.room = Room()

    class Token:
        def __init__(self, *_: str) -> None:
            pass

        def with_identity(self, _: str) -> Token:
            return self

        def with_grants(self, _: object) -> Token:
            return self

        def to_jwt(self) -> str:
            return "mocked-jwt"

    api = SimpleNamespace(
        LiveKitAPI=Client, AccessToken=Token,
        CreateRoomRequest=lambda **kwargs: kwargs, DeleteRoomRequest=lambda **kwargs: kwargs,
        VideoGrants=lambda **kwargs: kwargs,
    )
    monkeypatch.setitem(sys.modules, "livekit.api", api)
    service = LiveKitService(Settings(livekit_api_key="key", livekit_api_secret="secret", livekit_url="ws://test"))
    room = await service.create_room("session")
    assert room == "translation-session"
    assert await service.generate_token("user", room) == "mocked-jwt"
    await service.end_room("session")
    assert len(requests) == 2
