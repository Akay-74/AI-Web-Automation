"""The optional API key must gate the API and WebSocket when set, and stay out
of the way when it is not (local development)."""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api.auth import is_valid_key
from app.config import get_settings
from app.main import app

# A malformed UUID fails path validation (422) *after* auth has passed, so the
# status code tells us whether the request got through without touching the DB.
_PROBE = "/api/tasks/not-a-uuid"


@pytest.fixture
def client():
    # No context manager: the lifespan (table creation) is not needed here.
    return TestClient(app)


@pytest.fixture
def key_required(monkeypatch):
    monkeypatch.setattr(get_settings(), "api_key", "s3cret")
    return "s3cret"


@pytest.fixture
def key_disabled(monkeypatch):
    monkeypatch.setattr(get_settings(), "api_key", "")


def test_blank_key_disables_the_check(key_disabled):
    assert is_valid_key(None)
    assert is_valid_key("anything")


def test_key_must_match_exactly(key_required):
    assert is_valid_key("s3cret")
    assert not is_valid_key(None)
    assert not is_valid_key("")
    assert not is_valid_key("s3cret ")
    assert not is_valid_key("wrong")


def test_http_open_when_disabled(client, key_disabled):
    assert client.get(_PROBE).status_code == 422


def test_http_rejects_missing_key(client, key_required):
    assert client.get(_PROBE).status_code == 401


def test_http_rejects_wrong_key(client, key_required):
    assert client.get(_PROBE, headers={"X-API-Key": "wrong"}).status_code == 401


def test_http_accepts_right_key(client, key_required):
    assert client.get(_PROBE, headers={"X-API-Key": key_required}).status_code == 422


def test_results_router_is_protected_too(client, key_required):
    assert client.get("/api/results/not-a-uuid").status_code == 401


def test_health_stays_public(client, key_required):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["auth_required"] is True


_WS_PATH = "/ws/tasks/00000000-0000-0000-0000-000000000000"


def test_websocket_rejects_missing_key(client, key_required):
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(_WS_PATH):
            pass
    assert exc.value.code == 1008


def test_websocket_accepts_right_key(client, key_required):
    with client.websocket_connect(f"{_WS_PATH}?api_key={key_required}") as ws:
        ws.close()
