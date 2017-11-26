import asyncio
import logging
import time
from protocodecs import SimpleJsonCodec

logging.basicConfig()
logger = logging.getLogger("pycortex")
logger.setLevel(logging.INFO)

class TimeSource:
    def get_time(self):
        return time.time()

_cache = {}
_entry_limit = 4096
_time_source = TimeSource()

def clear_cache():
    global _cache
    _cache = {}

def set_entry_limit(limit):
    global _entry_limit
    _entry_limit = limit

def server_factory(codec):
    def create():
        return Server(codec)
    return create


class Entry:
    def __init__(self, value):
        self.value = value
        self.touch()

    def touch(self):
        self.last_access = _time_source.get_time()

    def __repr__(self):
        return '<Entry value="%s" last_access=%d>' % (self.value, self.last_access)

class Server(asyncio.Protocol):
    def __init__(self, codec):
        self._codec = codec
        self._transport = None

    def _return_error(self):
        self._transport.write(self._codec.encode_response(None, True))

    def _return_ack(self):
        self._transport.write(self._codec.encode_response(None, False))

    def connection_made(self, transport):
        self._transport = transport

    def connection_lost(self, reason):
        pass

    def data_received(self, data):
        request = self._codec.decode_request(data)
        if request.method == "GET":
            try:
                entry = _cache[request.key]
            except KeyError:
                # Cache miss
                self._return_error()
            else:
                # Cache hit
                entry.touch()
                self._transport.write(self._codec.encode_response(entry.value, False))
        elif request.method == "SET":
            _cache[request.key] = Entry(request.value)
            if len(_cache) > _entry_limit:
                self.discard_oldest()
            self._return_ack()
        elif request.method == "EVICT":
            try:
                del _cache[request.key]
            except KeyError:
                self._return_error()
            else:
                self._return_ack()
        else:
            logger.warning('Unknown method "%s" from client' % (request.method))


    def discard_oldest(self):
        # TODO: This search is linear and slow once the limit is reached.
        # It might be better to consider an ordered set/heap where the
        # amortied cost of keeping it ordered is lower.
        oldest_time = _time_source.get_time()
        oldest_key = None
        for key, entry in _cache.items():
            if entry.last_access < oldest_time:
                oldest_time = entry.last_access
                oldest_key = key
        del _cache[oldest_key]

def start(loop, codec, host='0.0.0.0', port=1234):

    start_coro = loop.create_server(server_factory(codec) , host, port)

    server = loop.run_until_complete(start_coro)
    logger.info("Serving on %s:%d", host, port)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt")

    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()


if __name__ == '__main__':
    loop = asyncio.get_event_loop();
    start(loop, SimpleJsonCodec())
