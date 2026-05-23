import pytest

from app.main import health_check


class _FakeDB:
    async def command(self, _: str):
        return {"ok": 1}


@pytest.mark.asyncio
async def test_health_endpoint(monkeypatch):
    monkeypatch.setattr("app.main.get_database", lambda: _FakeDB())
    response = await health_check()
    assert response == {"status": "ok"}
