from monstr.relay.relay import Relay
from monstr.relay.exceptions import NostrCommandException, NostrNoticeException, NostrNotAuthenticatedException
from monstr.event.event import Event
from monstr.event.persist import RelayEventStoreInterface, ARelayEventStoreInterface

import logging, json
from typing import Union

from nqsafe import PQEvent



class PQRelay(Relay):
    pq: bool = True

    async def _do_event(self, req_json, ws):
        if len(req_json) <= 1:
            raise NostrNoticeException('EVENT command missing event data')
        
        len_pubkey = len(req_json[1]['pubkey'])
        print(f"len pubkey is: {len_pubkey}")

        if len_pubkey > 64:
            evt = PQEvent.load(req_json[1])   
        else:
            evt = Event.load(req_json[1])
            
            
            
        if not evt.is_valid():
            raise NostrCommandException(event_id=evt.id,
                                       success=False,
                                       message='invalid: signature validation failed')
        



        # check against any acceptors we've been handed
        # acceptors may throw NostrCommandException, NostrNoticeException, NostrNotAuthenticatedException
        for c_accept in self._accept_req:
            c_accept.accept_post(ws, evt)

        try:
            saved = False
            if self._store:
                if isinstance(self._store, ARelayEventStoreInterface):
                    await self._store.add_event(evt)
                else:
                    self._store.add_event(evt)
                logging.debug('Relay::_do_event event sent to store %s ' % evt)
                saved = True
        except Exception as e:
            logging.debug('Relay::store event failed - %s' % e)

        # do the subs
        await self._check_subs(evt)

        raise NostrCommandException(event_id=evt.id,
                                    success=saved,
                                    message='')
    
    async def _do_sub(self, req_json, ws):
        logging.info('subscription pqr requested - %s' % req_json)
        # get sub_id and filter fro the json
        if len(req_json) <= 1:
            raise NostrNoticeException('REQ command missing sub_id')
        sub_id = req_json[1]
        if not isinstance(sub_id, str):
            raise NostrNoticeException('sub id should be string, received %s' % type(sub_id))

        # if we don't get a filter default to {} rather than error?
        # did this because loquaz doesnt supply so assuming this is permited
        filter = {}
        if len(req_json) > 2:
            filter = req_json[2:]
            # raise NostrCommandException('REQ command missing filter')

        # this user already subscribed under same sub_id
        socket_id = ws.id
        if sub_id in self._ws[socket_id]['subs']:
            raise NostrNoticeException('REQ command for sub_id that already exists - %s' % sub_id)
        # this sub would put us over max for this socket
        sub_count = len(self._ws[socket_id]['subs'])
        if sub_count >= self._max_sub:
            raise NostrNoticeException('REQ new sub_id %s not allowed, already at max subs=%s' % (sub_id, self._max_sub))

        the_sub = self._ws[socket_id]['subs'][sub_id] = {
            'id': sub_id,
            'filter': filter
        }

        logging.info('Relay::_do_sub subscription added %s (%s)' % (sub_id, filter))

        # get and send any stored events we have and send back
        evts = []
        if self._store:
            if isinstance(self._store, ARelayEventStoreInterface):
                evts = await self._store.get_filter(filter)
            else:
                evts = self._store.get_filter(filter)

        for c_evt in evts:
            logging.info(f"send c_evt {c_evt}")
            await self._send_event(ws, the_sub, c_evt)

        await self._send_eose(ws, sub_id)
    
