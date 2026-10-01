from __future__ import annotations

from httpx import AsyncClient


async def test_otp_authentication_and_profile_update(client: AsyncClient) -> None:
    sent = await client.post("/api/v1/auth/send-otp", json={"phone": "+251911000000"})
    assert sent.status_code == 200
    verified = await client.post("/api/v1/auth/verify-otp", json={"phone": "+251911000000", "code": "123456"})
    assert verified.status_code == 200
    token = verified.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert (await client.get("/api/v1/users/me", headers=headers)).json()["user"]["phone"] == "+251911000000"
    updated = await client.patch("/api/v1/users/me", headers=headers, json={"display_name": "Zoe", "language_preferences": ["am", "en"]})
    assert updated.status_code == 200
    assert updated.json()["user"]["display_name"] == "Zoe"


async def test_invalid_otp_is_rejected(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/verify-otp", json={"phone": "+251911000001", "code": "000000"})
    assert response.status_code == 401
