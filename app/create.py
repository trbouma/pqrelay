"""Create a disposable ML-DSA-44 event without printing its secret key."""
from nqsafe import PQEvent, get_backend

if __name__ == "__main__":
    keys = get_backend().generate_signing_keypair()
    event = PQEvent(pub_key=keys.public_key.hex(), content="quantum event",
                    tags=[["t", "quantum_safe"]], kind=100001)
    event.sign(keys.secret_key.hex())
    print(event.data())
    print(f"valid: {event.is_valid()}")
