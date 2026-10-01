from __future__ import annotations

import importlib
import inspect
from typing import Any

from config import Settings, get_settings


async def _maybe_await(value: Any) -> Any:
    return await value if inspect.isawaitable(value) else value


class LiveKitService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @staticmethod
    def room_name(session_id: str) -> str:
        return f"translation-{session_id}"

    def _api(self) -> Any | None:
        if not (self.settings.livekit_api_key and self.settings.livekit_api_secret):
            return None
        try:
            return importlib.import_module("livekit.api")
        except ImportError:
            return None

    async def create_room(self, session_id: str) -> str:
        room_name = self.room_name(session_id)
        api = self._api()
        if api is None:
            return room_name
        client = api.LiveKitAPI(self.settings.livekit_url)
        await _maybe_await(client.room.create_room(api.CreateRoomRequest(name=room_name)))
        return room_name

    async def generate_token(self, user_id: str, room_name: str) -> str:
        api = self._api()
        if api is None:
            return f"mock-livekit-token:{user_id}:{room_name}"
        token = api.AccessToken(self.settings.livekit_api_key, self.settings.livekit_api_secret)
        token = token.with_identity(user_id).with_grants(api.VideoGrants(room_join=True, room=room_name))
        return str(token.to_jwt())

    async def end_room(self, session_id: str) -> None:
        api = self._api()
        if api is None:
            return
        client = api.LiveKitAPI(self.settings.livekit_url)
        await _maybe_await(client.room.delete_room(api.DeleteRoomRequest(room=self.room_name(session_id))))
