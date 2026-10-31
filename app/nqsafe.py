"""Nonstandard PQ events: Stroma crypto with Monstr relay/storage compatibility."""
from functools import lru_cache
import json
import os
import re

from monstr.event.event import Event
from stroma import Event as StromaEvent
from stroma.pq import PQBackend


@lru_cache(maxsize=1)
def get_backend():
    return PQBackend(os.environ.get("PQRELAY_LIBOQS_PATH", "/usr/local/lib/liboqs.so"))


def _hex(value, size):
    return isinstance(value, str) and len(value) == size * 2 and re.fullmatch(r"[0-9a-f]+", value) is not None


def validate_shape(data):
    if not isinstance(data, dict):
        raise ValueError("event must be an object")
    if not _hex(data.get("id"), 32):
        raise ValueError("invalid event id")
    public = data.get("pubkey")
    if not (_hex(public, 32) or _hex(public, 1312)):
        raise ValueError("only secp256k1 and ML-DSA-44 public keys are supported")
    if not _hex(data.get("sig"), 64 if len(public) == 64 else 2420):
        raise ValueError("invalid signature encoding or size")
    for field in ("created_at", "kind"):
        if not isinstance(data.get(field), int) or isinstance(data[field], bool) or not 0 <= data[field] <= 2**63 - 1:
            raise ValueError(f"invalid {field}")
    if not isinstance(data.get("content"), str):
        raise ValueError("content must be a string")
    tags = data.get("tags")
    if not isinstance(tags, list) or any(
        not isinstance(tag, list) or not tag or any(not isinstance(v, str) for v in tag)
        for tag in tags
    ):
        raise ValueError("tags must be arrays of strings")


class PQEvent(Event):
    sigalg = "ML-DSA-44"

    def _stroma_event(self):
        return StromaEvent.load(self.data())

    def sign(self, priv_key):
        if not isinstance(priv_key, str):
            raise ValueError("private key must be hex")
        event = self._stroma_event()
        if len(priv_key) == 64:
            event.sign(priv_key)
            self._pub_key, self._id, self._sig = event.pub_key, event.id, event.sig
        else:
            if not _hex(priv_key, 2560) or not _hex(self.pub_key, 1312):
                raise ValueError("ML-DSA-44 key sizes required")
            event_id = event.calculate_id()
            backend = get_backend()
            signature = backend.sign(bytes.fromhex(event_id), bytes.fromhex(priv_key), context=b"")
            if not backend.verify(bytes.fromhex(event_id), signature, bytes.fromhex(self.pub_key), context=b""):
                raise ValueError("signing key does not match event public key")
            self._id, self._sig = event_id, signature.hex()

    def is_valid(self):
        try:
            data = self.data()
            validate_shape(data)
            event = StromaEvent.load(data)
            if event.calculate_id() != data["id"]:
                return False
            if len(data["pubkey"]) == 64:
                return event.is_valid()
            return get_backend().verify(bytes.fromhex(data["id"]), bytes.fromhex(data["sig"]),
                                        bytes.fromhex(data["pubkey"]), context=b"")
        except (TypeError, ValueError):
            return False

    @staticmethod
    def load(event_data, validate=False):
        data = json.loads(event_data) if isinstance(event_data, str) else event_data
        validate_shape(data)
        event = PQEvent(id=data["id"], sig=data["sig"], kind=data["kind"],
                        content=data["content"], tags=data["tags"], pub_key=data["pubkey"],
                        created_at=data["created_at"])
        return event if not validate or event.is_valid() else None
