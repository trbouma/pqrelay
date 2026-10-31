import asyncio
import logging

from monstr.event.persist_sqlite import RelaySQLiteEventStore
from pqr import PQRelay
from nqsafe import get_backend

from config import Settings

settings = Settings()


async def run_relay():
    get_backend()  # Fail startup rather than install or downgrade at runtime.
    relay_store = RelaySQLiteEventStore(db_file=settings.SERVICE_RELAY_DB)
    try:
        relay_store.create()
    except:
        pass
    r = PQRelay(store=relay_store)
   
    try:
        await r.start(host=settings.LOCAL_RELAY_HOST, port=settings.LOCAL_RELAY_PORT)
    finally:
        # Monstr's runner invokes its shutdown hook to close active WebSockets.
        # It may not exist yet if startup failed before runner initialization.
        if getattr(r, '_runner', None) is not None:
            await r.end_background()


def main():
    logging.getLogger().setLevel(logging.DEBUG)
    logging.debug(f"{settings.LOCAL_RELAY_HOST}")
    try:
        asyncio.run(run_relay())
    except KeyboardInterrupt:
        logging.info("Relay stopped")


if __name__ == '__main__':
    main()
