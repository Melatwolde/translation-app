from __future__ import annotations

import base64

from httpx import AsyncClient


async def test_process_audio_returns_translation(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/send-otp", json={"phone": "+251911000002"})
    verified = await client.post("/api/v1/auth/verify-otp", json={"phone": "+251911000002", "code": "123456"})
    headers = {"Authorization": f"Bearer {verified.json()['access_token']}"}
    session = await client.post("/api/v1/sessions", headers=headers, json={"source_language": "am", "target_language": "en"})
    response = await client.post(f"/api/v1/sessions/{session.json()['id']}/process-audio", headers=headers, json={"audio_base64": base64.b64encode(b"\x00\x00").decode()})
    assert response.status_code == 200
    assert response.json()["segment"]["source_text"] == "transcript:am"
