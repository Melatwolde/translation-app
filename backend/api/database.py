from __future__ import annotations

import asyncio
import inspect
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from config import get_settings
from models.session import SessionCreate, SessionResponse
from models.user import UserProfile, UserProfileUpdate


class Database(Protocol):
    async def upsert_user(self, user_id: UUID, phone: str) -> UserProfile: ...
    async def get_user(self, user_id: UUID) -> UserProfile | None: ...
    async def update_user(self, user_id: UUID, update: UserProfileUpdate) -> UserProfile | None: ...
    async def create_session(self, user_id: UUID, request: SessionCreate) -> SessionResponse: ...
    async def get_session(self, session_id: UUID) -> SessionResponse | None: ...
    async def end_session(self, session_id: UUID) -> SessionResponse | None: ...


class InMemoryDatabase:
    def __init__(self) -> None:
        self.users: dict[UUID, UserProfile] = {}
        self.sessions: dict[UUID, SessionResponse] = {}

    async def upsert_user(self, user_id: UUID, phone: str) -> UserProfile:
        existing = self.users.get(user_id)
        if existing is not None:
            return deepcopy(existing)
        user = UserProfile(id=user_id, phone=phone, created_at=datetime.now(UTC))
        self.users[user_id] = user
        return deepcopy(user)

    async def get_user(self, user_id: UUID) -> UserProfile | None:
        user = self.users.get(user_id)
        return deepcopy(user) if user else None

    async def update_user(self, user_id: UUID, update: UserProfileUpdate) -> UserProfile | None:
        user = self.users.get(user_id)
        if user is None:
            return None
        values = update.model_dump(exclude_unset=True)
        self.users[user_id] = user.model_copy(update=values)
        return deepcopy(self.users[user_id])

    async def create_session(self, user_id: UUID, request: SessionCreate) -> SessionResponse:
        from uuid import uuid4
        session = SessionResponse(id=uuid4(), user_id=user_id, status="active", created_at=datetime.now(UTC), **request.model_dump())
        self.sessions[session.id] = session
        return deepcopy(session)

    async def get_session(self, session_id: UUID) -> SessionResponse | None:
        session = self.sessions.get(session_id)
        return deepcopy(session) if session else None

    async def end_session(self, session_id: UUID) -> SessionResponse | None:
        session = self.sessions.get(session_id)
        if session is None:
            return None
        self.sessions[session_id] = session.model_copy(update={"status": "ended", "ended_at": datetime.now(UTC)})
        return deepcopy(self.sessions[session_id])


class SupabaseDatabase:
    """Supabase adapter; selected only when service credentials are configured."""

    def __init__(self, client: Any) -> None:
        self.client = client

    async def _execute(self, query: Any) -> Any:
        execute = query.execute
        if inspect.iscoroutinefunction(execute):
            return await execute()
        return await asyncio.to_thread(execute)

    @staticmethod
    def _user(row: dict[str, Any]) -> UserProfile:
        return UserProfile.model_validate(row)

    @staticmethod
    def _session(row: dict[str, Any]) -> SessionResponse:
        return SessionResponse.model_validate(row)

    async def upsert_user(self, user_id: UUID, phone: str) -> UserProfile:
        response = await self._execute(self.client.table("profiles").upsert({"id": str(user_id), "phone": phone}))
        return self._user(response.data[0])

    async def get_user(self, user_id: UUID) -> UserProfile | None:
        response = await self._execute(self.client.table("profiles").select("*").eq("id", str(user_id)))
        return self._user(response.data[0]) if response.data else None

    async def update_user(self, user_id: UUID, update: UserProfileUpdate) -> UserProfile | None:
        response = await self._execute(self.client.table("profiles").update(update.model_dump(exclude_unset=True)).eq("id", str(user_id)))
        return self._user(response.data[0]) if response.data else None

    async def create_session(self, user_id: UUID, request: SessionCreate) -> SessionResponse:
        from uuid import uuid4
        payload = {"id": str(uuid4()), "user_id": str(user_id), **request.model_dump()}
        response = await self._execute(self.client.table("translation_sessions").insert(payload))
        return self._session(response.data[0])

    async def get_session(self, session_id: UUID) -> SessionResponse | None:
        response = await self._execute(self.client.table("translation_sessions").select("*").eq("id", str(session_id)))
        return self._session(response.data[0]) if response.data else None

    async def end_session(self, session_id: UUID) -> SessionResponse | None:
        response = await self._execute(self.client.table("translation_sessions").update({"status": "ended", "ended_at": datetime.now(UTC).isoformat()}).eq("id", str(session_id)))
        return self._session(response.data[0]) if response.data else None


_database: Database = InMemoryDatabase()


async def get_database() -> Database:
    global _database
    settings = get_settings()
    if isinstance(_database, InMemoryDatabase) and settings.supabase_url and settings.supabase_key:
        from supabase import create_client
        _database = SupabaseDatabase(create_client(settings.supabase_url, settings.supabase_key))
    return _database


def set_database(database: Database) -> None:
    global _database
    _database = database
