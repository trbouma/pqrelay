from monstr.event.event import Event
from monstr.encrypt import Keys
from monstr.client.client import Client, ClientPool
from typing import List

import asyncio, json

from nqsafe import PQEvent
import oqs

if __name__ == "__main__":

    sigalg = "ML-DSA-44"
    signer = oqs.Signature(sigalg)
    signer_public_key = signer.generate_keypair()
    
    pq_pubkey = signer_public_key.hex()

    secret_key = signer.export_secret_key()

    content = "quantum event again"
    tags = ["t", "quantum_safe"]
    pq_event = PQEvent( pub_key=pq_pubkey,
                       content=content,
                       tags = tags,
                       kind = 100001
                       
                       
                       )

    pq_event._get_id()
    pq_event.id = pq_event._id

    signer_public_key_bytes = bytes.fromhex(pq_pubkey)
   
    
    

    pq_event.sign(priv_key=secret_key.hex())
    print(f"nostr pqevent {pq_event.data()}")
    print(f"is valid: {pq_event.is_valid()}")