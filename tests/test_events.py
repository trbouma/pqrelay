import copy
import json
import os

import pytest
from stroma import Event, Keys, RelayClient

from nqsafe import PQEvent, get_backend
from pqclient import query_events


def classical():
    event = Event(content="test", tags=[["t", "test"]], kind=1711)
    event.sign(Keys())
    return event.data()


def test_relay_metadata_preserves_supported_nips():
    from monstr.relay.relay import Relay
    from pqr import PQRelay

    info = PQRelay().relay_information
    assert info['name'] == 'pqrelay'
    assert info['software'] == 'https://github.com/trbouma/pqrelay'
    assert info['version'] == '0.1.0'
    assert 'ML-DSA-44' in info['description']
    assert 'not a standardized NIP' in info['description']
    assert info['supported_nips'] == Relay().relay_information['supported_nips']
    assert PQRelay(name='My relay').relay_information['name'] == 'My relay'


def test_classical_roundtrip():
    data = classical()
    assert PQEvent.load(data, validate=True).data() == data
    event = PQEvent(content="signed through adapter", kind=1)
    event.sign(Keys().private_key_hex())
    assert event.is_valid()


@pytest.mark.parametrize("field,value", [("content", "changed"), ("tags", [["x", "y"]]),
    ("kind", 2), ("created_at", 1), ("id", "0" * 64), ("pubkey", "1" * 64), ("sig", "0" * 128)])
def test_classical_tampering(field, value):
    data = classical()
    data[field] = value
    assert not PQEvent.load(data).is_valid()


@pytest.mark.parametrize("field,value", [("pubkey", "a" * (897 * 2)),  # Falcon-512
    ("sig", "a"), ("id", None), ("tags", ["t", "bad"]), ("kind", True),
    ("created_at", "123"), ("content", {})])
def test_malformed_and_unsupported(field, value):
    data = classical()
    data[field] = value
    with pytest.raises(ValueError):
        PQEvent.load(data)


@pytest.fixture
def pq_event():
    if not os.environ.get("PQRELAY_LIBOQS_PATH"):
        pytest.skip("Set PQRELAY_LIBOQS_PATH to enable native ML-DSA tests")
    keys = get_backend().generate_signing_keypair()
    event = PQEvent(pub_key=keys.public_key.hex(), content="PQ test", tags=[["t", "test"]], kind=1711)
    event.sign(keys.secret_key.hex())
    return event


def test_pq_roundtrip_and_tampering(pq_event):
    assert pq_event.is_valid()
    assert PQEvent.load(json.dumps(pq_event.data()), validate=True)
    for field, value in (("content", "changed"), ("tags", [["a", "b"]]),
                         ("created_at", 1), ("kind", 2), ("sig", "0" * 4840)):
        data = copy.deepcopy(pq_event.data())
        data[field] = value
        assert not PQEvent.load(data).is_valid()


@pytest.mark.asyncio
async def test_relay_sqlite_publish_query_and_rejection(tmp_path, pq_event):
    import aiohttp
    from monstr.event.persist_sqlite import RelaySQLiteEventStore
    from pqr import PQRelay

    store = RelaySQLiteEventStore(db_file=str(tmp_path / "relay.db"))
    store.create()
    relay = PQRelay(store=store)
    await relay.start(host="127.0.0.1", port=0, block=False)
    port = next(iter(relay._runner.sites))._server.sockets[0].getsockname()[1]
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://127.0.0.1:{port}/") as response:
                info = await response.json(content_type=None)
                assert info == relay.relay_information
                assert info['software'] == 'https://github.com/trbouma/pqrelay'
            async with session.ws_connect(f"http://127.0.0.1:{port}/") as ws:
                ids = []
                for data in (classical(), pq_event.data()):
                    await ws.send_json(["EVENT", data])
                    reply = await ws.receive_json(timeout=5)
                    assert reply[:3] == ["OK", data["id"], True]
                    ids.append(data["id"])
                bad = pq_event.data()
                bad["content"] = "tampered"
                await ws.send_json(["EVENT", bad])
                assert (await ws.receive_json(timeout=5))[2] is False
                await ws.send_json(["EVENT", {"pubkey": None}])
                assert (await ws.receive_json(timeout=5))[2] is False
                await ws.send_json(["REQ", "test", {"ids": ids}])
                received = []
                while True:
                    reply = await ws.receive_json(timeout=5)
                    if reply[0] == "EOSE":
                        break
                    assert PQEvent.load(reply[2]).is_valid()
                    received.append(reply[2]["id"])
                assert set(received) == set(ids)
        # The demo's Stroma transport must preserve nonstandard PQ fields.
        client = RelayClient(f"ws://127.0.0.1:{port}/")
        assert (await client.publish(pq_event)).accepted
        # Standard Stroma queries intentionally reject nonstandard signatures.
        assert await client.query({"ids": [pq_event.id]}) == []
        queried = await query_events(f"ws://127.0.0.1:{port}/", {"ids": [pq_event.id]})
        assert len(queried) == 1
        assert PQEvent.load(queried[0].data()).is_valid()
    finally:
        await relay.end_background()
