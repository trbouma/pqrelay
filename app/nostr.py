"""Publish and retrieve disposable classical and ML-DSA-44 events."""
import asyncio
import json
import os
from stroma import Event, Keys, RelayClient
from nqsafe import PQEvent, get_backend
from pqclient import query_events

def relay_pool_from_env():
    value = os.environ.get("RELAY_POOL", "ws://localhost:8735")
    relays = [url.strip() for url in value.split(",") if url.strip()]
    if not relays:
        raise ValueError("RELAY_POOL must contain at least one relay URL")
    return relays


RELAY_POOL = relay_pool_from_env()


def display_event(event, algorithm, stage):
    # Only public wire fields; never serialize a keypair or backend object.
    data = event.data()
    public = {field: data.get(field) for field in
              ("id", "pubkey", "created_at", "kind", "tags", "content", "sig")}
    print(f"\n--- {algorithm}: {stage} ---")
    print(json.dumps(public, indent=2, ensure_ascii=False))
    print(f"Public key: {len(bytes.fromhex(public['pubkey']))} bytes")
    if public['sig']:
        print(f"Signature: {len(bytes.fromhex(public['sig']))} bytes")
    if algorithm == "ML-DSA-44":
        print("Signing input: 32-byte event ID (SHA-256 of canonical event); context: empty")


async def main():
    keys = get_backend().generate_signing_keypair()
    pq_event = PQEvent(pub_key=keys.public_key.hex(), content="quantum event",
                       tags=[["t", "quantum_safe"]], kind=1711)
    pq_event._get_id()
    display_event(pq_event, "ML-DSA-44", "before signing")
    pq_event.sign(keys.secret_key.hex())
    regular_keys = Keys()
    regular = Event(kind=1711, content="regular event", pub_key=regular_keys.public_key_hex())
    display_event(regular, "secp256k1 / BIP-340", "before signing")
    regular.sign(regular_keys)
    for url in RELAY_POOL:
        client = RelayClient(url)
        for event, algorithm in ((regular, "secp256k1 / BIP-340"), (pq_event, "ML-DSA-44")):
            display_event(event, algorithm, f"signed event publishing to {url}")
            result = await client.publish(event)
            if not result.accepted:
                raise RuntimeError(f"Relay rejected event: {result.message}")
            print(f"Accepted: {event.id}")
        events = await query_events(url, {"ids": [regular.id, pq_event.id]})
        for event in events:
            valid = PQEvent.load(event.data()).is_valid()
            print(f"Retrieved: {event.id}; valid: {valid}")
            if not valid:
                raise RuntimeError("Retrieved event failed verification")


if __name__ == "__main__":
    asyncio.run(main())


