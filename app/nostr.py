"""Publish and retrieve disposable classical and ML-DSA-44 events."""
import asyncio
from stroma import Event, Keys, RelayClient
from nqsafe import PQEvent, get_backend
from pqclient import query_events

RELAY_POOL = ["ws://localhost:8735"]


async def main():
    keys = get_backend().generate_signing_keypair()
    pq_event = PQEvent(pub_key=keys.public_key.hex(), content="quantum event",
                       tags=[["t", "quantum_safe"]], kind=1711)
    pq_event.sign(keys.secret_key.hex())
    regular = Event(kind=1711, content="regular event")
    regular.sign(Keys())
    for url in RELAY_POOL:
        client = RelayClient(url)
        for event in (regular, pq_event):
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


