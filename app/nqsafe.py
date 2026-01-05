from monstr.event.event import Event
from typing import Union
import json
import secp256k1

import oqs


class PQEvent(Event):
    test: str
    sigalg: str = "ML-DSA-44"

    def sign(self, priv_key):
        
        print(f"length of private key {len(priv_key)}")
        if len(priv_key) > 64: 
            signer = oqs.Signature(self.sigalg,secret_key=bytes.fromhex(priv_key))
            # print(f"sign with {priv_key}")
            self._get_id()
            id_bytes = (bytes(bytearray.fromhex(self._id)))
        
            signature = signer.sign(id_bytes)
            self._sig = signature.hex()
        else:
            self._get_id()

           
            pk = secp256k1.PrivateKey()
            pk.deserialize(priv_key)

            id_bytes = (bytes(bytearray.fromhex(self._id)))
            sig = pk.schnorr_sign(id_bytes, bip340tag='', raw=True)
            sig_hex = sig.hex()

            self._sig = sig_hex

    def is_valid(self):
        is_valid = False
        try:
            if len(self.pub_key) > 64:
            
                verifier = oqs.Signature(self.sigalg)

                id_bytes = (bytes(bytearray.fromhex(self.id)))
                sig_bytes = (bytes(bytearray.fromhex(self.sig)))
                pub_key_bytes = (bytes(bytearray.fromhex(self.pub_key)))

                is_valid = verifier.verify(id_bytes, sig_bytes, pub_key_bytes)
            else:
                
                pub_key = secp256k1.PublicKey(bytes.fromhex('02'+self._pub_key),
                                        raw=True)

                is_valid = pub_key.schnorr_verify(
                            msg=bytes.fromhex(self._id),
                            schnorr_sig=bytes.fromhex(self._sig),
                            bip340tag='', raw=True)
        except:
            is_valid = False   
                 
        return is_valid
    
    @staticmethod    
    def load(event_data: Union[str, dict], validate=False) -> 'PQEvent':
        """
            return a Event object either from a dict or json str this replaces the old from_JSON method
            that was actually just from a string...
            if validate is set True will test the event sig, if it's not None will be returned

        """
        if isinstance(event_data, str):
            try:
                event_data = json.loads(event_data)
            except Exception as e:
                event_data = {}

        id = None
        if 'id' in event_data:
            id = event_data['id']

        sig = None
        if 'sig' in event_data:
            sig = event_data['sig']

        kind = None
        if 'kind' in event_data:
            kind = event_data['kind']

        content = None
        if 'content' in  event_data:
            content = event_data['content']

        tags = None
        if 'tags' in event_data:
            tags = event_data['tags']

        pub_key = None
        if 'pubkey' in event_data:
            pub_key = event_data['pubkey']

        created_at = None
        if 'created_at' in event_data:
            created_at = event_data['created_at']

        ret = PQEvent(
            id=id,
            sig=sig,
            kind=kind,
            content=content,
            tags=tags,
            pub_key=pub_key,
            created_at=created_at
        )

        # None ret if validating and the evnt is not valid
        if validate is True and ret.is_valid() is False:
            ret = None

        return ret


if __name__ == "main":
    print("nostr nqsafe")