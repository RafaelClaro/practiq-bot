import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ["ANTHROPIC_API_KEY"] = "test-key"

from app.main import app

client = TestClient(app)


# ── Fixtures ──
def mock_anthropic_response(text: str):
    mock = MagicMock()
    mock.content = [MagicMock(text=text)]
    return mock


# ── Health check ──
def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── Chat — happy path ──
@patch("app.main.client.messages.create")
def test_chat_simple(mock_create):
    mock_create.return_value = mock_anthropic_response(
        "Olá! Qual o maior problema operacional que você enfrenta hoje?"
    )
    r = client.post("/chat", json={"message": "oi", "history": [], "session_id": "test-1"})
    assert r.status_code == 200
    assert "reply" in r.json()
    assert len(r.json()["reply"]) > 0


# ── Chat — com histórico ──
@patch("app.main.client.messages.create")
def test_chat_with_history(mock_create):
    mock_create.return_value = mock_anthropic_response(
        "Entendo! A Practiq resolve exatamente isso — automação de confirmações que reduz faltas em até 70%."
    )
    payload = {
        "message": "tenho problema com faltas de clientes",
        "history": [
            {"role": "user", "content": "oi"},
            {"role": "assistant", "content": "Olá! Qual seu maior problema hoje?"},
        ],
        "session_id": "test-2",
    }
    r = client.post("/chat", json=payload)
    assert r.status_code == 200
    assert "reply" in r.json()


# ── Chat — mensagem vazia ──
@patch("app.main.client.messages.create")
def test_chat_empty_message(mock_create):
    mock_create.return_value = mock_anthropic_response("Como posso ajudar?")
    r = client.post("/chat", json={"message": "", "session_id": "test-3"})
    # aceita mas retorna resposta
    assert r.status_code in (200, 422)


# ── Chat — erro da API Anthropic ──
@patch("app.main.client.messages.create")
def test_chat_anthropic_error(mock_create):
    import anthropic as ant
    mock_create.side_effect = ant.APIError("rate limit", request=MagicMock(), body=None)
    r = client.post("/chat", json={"message": "teste", "session_id": "test-4"})
    assert r.status_code == 502


# ── Payload sem session_id ──
@patch("app.main.client.messages.create")
def test_chat_no_session(mock_create):
    mock_create.return_value = mock_anthropic_response("Posso ajudar!")
    r = client.post("/chat", json={"message": "quero saber mais"})
    assert r.status_code == 200
