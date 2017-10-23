import json

class Request:
    def __init__(self, method, key, value):
        self.method = method
        self.key = key
        self.value = value


class Response:
    def __init__(self, value, error):
        self.value = value
        self.error = error

    def is_hit(self):
        return (self.value is not None) and (self.error == False)

    def get_value(self):
        return self.value

    def is_error(self):
        return self.error

    def is_ack(self):
        return (self.value is None) and (self.error == False)

"""
A very simple cache protocol.
Keys and values are interpreted as utf-8 strings and keys must be alphanumerical.

Requests
========
Set: {"m": "SET", "k": <key>, "v": value}
Get: {"m": "GET", "k": <key>}
Evict: {"m": "EVICT", "k": <key>}
Clear: {"m": "CLEAR"}

Responses
=========
Hit: (Get           {"v": <value>, "e": False}
Miss (Get, Delete): {"v": None, "e": True}
Ack (Set, Delete):  {"v": None, "e": False}
"""
class SimpleJsonCodec:
    def _check_key(self, key):
        if not (type(key) is str):
            raise TypeError("Key must be of type str.")
        if not key.isalnum():
            raise ValueError('Key must be alphanumeric.')

    def _encode_request(self, method, key, value=None):
        self._check_key(key)
        if value:
            return bytes(json.dumps({'m': method, 'k': key, "v": value}), 'utf-8')
        return bytes(json.dumps({'m': method, 'k': key}), 'utf-8')

    """ Used by client """
    def encode_set(self, key, value):
        self._check_key(key)
        if not (type(value) is str):
            raise TypeError("Value must be of type str.")
        #if timeout is not None:
        #    if (not type(timeout) is int):
        #        raise TypeError("Timeout must be of type int.")

        return self._encode_request('SET', key, value)

    """ Used by client """
    def encode_get(self, key):
        self._check_key(key)
        return self._encode_request('GET', key)

    """ Used by client """
    def decode_response(self, data):
        data = data.decode('utf-8')
        j = json.loads(data)
        response = Response(j["v"], j["e"])
        return response

    """ Used by server """
    def decode_request(self, data):
        data = data.decode('utf-8')
        j = json.loads(data)
        self._check_key(j["k"])

        if not "k" in j:
            key = None
        else:
            key = j["k"]

        if not "v" in j:
            value = None
        else:
            value = j["v"]

        request = Request(j["m"], key, value)
        return request

    """ Used by server """
    def encode_response(self, value, error):
        return bytes(json.dumps({'v': value, 'e': error}), 'utf-8')
