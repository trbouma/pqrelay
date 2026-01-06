from monstr.event.event import Event
from monstr.encrypt import Keys
from monstr.client.client import Client, ClientPool
from typing import List

import asyncio, json

from nqsafe import PQEvent
import oqs

RELAY_POOL = ["ws://localhost:8735"]


async def publish(event: Event):
    
    async with ClientPool(RELAY_POOL) as c:
        print(f"publish regular event is valid {event.is_valid()}")
        
        c.publish(evt=event)

async def pqc_publish(event: PQEvent):
    
    async with ClientPool(RELAY_POOL) as c:
        print(f"publish pqc event is valid {event.is_valid()}")
        c.publish(evt=event)

async def events_to_query_with_pubkey(pubkey_list: List[str]):
    print(f"pubkey list: {pubkey_list}")

    FILTER = [{
                'limit': 100, 
                'authors'  :  pubkey_list,  
                }]
    
    print(FILTER)
    async with ClientPool(RELAY_POOL) as c:  
            events = await c.query(FILTER)           
        
    
    print(f"finished query {len(events)}")
    for each in events:
        pq = PQEvent().load(each.data())
        print(f"each: {pq.content} is valid: {pq.is_valid()}")
    
    return

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

    # You can modify the content after signing to see if there is a validation error
    # pq_event.content = "modified after signing"
    
    #Let's create a regular event
    regular_keys = Keys()
    regular_pubkey = regular_keys.public_key_hex()

    regular_event: Event = Event(   pub_key=regular_pubkey,
                                    kind = 100001,
                                    content="regular event")
    
    regular_event.sign(priv_key=regular_keys.private_key_hex())
    print(f"check to see if reqular event is valid {regular_event.is_valid()}")
    
    # You can modify the content after the signing to see if there are validation errors
    # regular_event.content ="modified after signing"

    asyncio.run(publish(regular_event))
    print("regular event published!")

    asyncio.run(pqc_publish(pq_event))
    print(f"check to see if pqc event is valid {pq_event.is_valid()}")

    print("pq event published!")

    event_data = pq_event.data()
    print(f"event data: {event_data}")
    new_pqc_event = PQEvent.load(event_data=event_data)
    print(f"new pqc event is valid {new_pqc_event.is_valid()}")

    keys_to_query = [regular_pubkey,pq_pubkey]
    asyncio.run(events_to_query_with_pubkey(keys_to_query))


