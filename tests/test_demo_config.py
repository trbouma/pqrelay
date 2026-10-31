import pytest

from nostr import relay_pool_from_env
from nostr import display_event
import json
from unittest.mock import Mock


def test_default_relay(monkeypatch):
    monkeypatch.delenv("RELAY_POOL", raising=False)
    assert relay_pool_from_env() == ["ws://localhost:8735"]


def test_beelink_override(monkeypatch):
    monkeypatch.setenv("RELAY_POOL", "ws://beelink:8735")
    assert relay_pool_from_env() == ["ws://beelink:8735"]


def test_multiple_relays(monkeypatch):
    monkeypatch.setenv("RELAY_POOL", " ws://beelink:8735, wss://relay.example.com ")
    assert relay_pool_from_env() == ["ws://beelink:8735", "wss://relay.example.com"]


def test_empty_pool_rejected(monkeypatch):
    monkeypatch.setenv("RELAY_POOL", " , ")
    with pytest.raises(ValueError, match="at least one"):
        relay_pool_from_env()


@pytest.mark.parametrize("signed", [False, True])
def test_event_display_includes_full_public_fields_only(capsys, signed):
    data = {"id": "a" * 64, "pubkey": "ab" * 1312, "created_at": 123,
            "kind": 1711, "tags": [["t", "quantum_safe"]], "content": "quantum event",
            "sig": "cd" * 2420 if signed else None, "secret_key": "NEVER_PRINT_THIS"}
    display_event(Mock(data=Mock(return_value=data)), "ML-DSA-44", "test")
    output = capsys.readouterr().out
    decoded, _ = json.JSONDecoder().raw_decode(output[output.index('{'):])
    assert decoded == {k: v for k, v in data.items() if k != "secret_key"}
    assert "NEVER_PRINT_THIS" not in output
    assert "Public key: 1312 bytes" in output
    assert ("Signature: 2420 bytes" in output) == signed
    assert "context: empty" in output
