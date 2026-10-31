"""Query adapter for pqrelay's nonstandard signature format.

Stroma's standard query client intentionally validates only classical NIP-01.
"""
import json
import secrets

import aiohttp

from nqsafe import PQEvent


async def query_events(url, filters, timeout=10):
    subscription = secrets.token_hex(8)
    events = {}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
        async with session.ws_connect(url, max_msg_size=1024 * 1024) as ws:
            await ws.send_json(["REQ", subscription, filters])
            async for message in ws:
                if message.type != aiohttp.WSMsgType.TEXT:
                    raise RuntimeError("Relay closed or failed before EOSE")
                data = json.loads(message.data)
                if not isinstance(data, list) or len(data) < 2 or data[1] != subscription:
                    continue
                if data[0] == "EOSE":
                    await ws.send_json(["CLOSE", subscription])
                    return list(events.values())
                if data[0] == "EVENT" and len(data) == 3:
                    event = PQEvent.load(data[2], validate=True)
                    if event is None:
                        raise ValueError("Retrieved event failed verification")
                    events[event.id] = event
                    if len(events) > 1000:
                        raise ValueError("Query exceeds 1000-event limit")
            raise RuntimeError("Relay closed before EOSE")
