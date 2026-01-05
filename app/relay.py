import asyncio
import logging
from monstr.relay.relay import Relay

from monstr.event.persist_sqlite import RelaySQLiteEventStore
from pqr import PQRelay
import os

from config import Settings

settings = Settings()

async def run_relay():
    relay_store = RelaySQLiteEventStore(db_file=settings.SERVICE_RELAY_DB)
    try:
        relay_store.create()
    except:
        pass
    r = PQRelay(store=relay_store)
   
    try:
        await r.start(host=settings.LOCAL_RELAY_HOST, port=settings.LOCAL_RELAY_PORT)
    except:
        pass

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    asyncio.run(run_relay())