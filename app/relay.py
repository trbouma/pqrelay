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
    except Exception as e:
        logging.debug(f"Failed to start{e}")
        pass

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    logging.debug(f"{settings.LOCAL_RELAY_HOST}")
    asyncio.run(run_relay())