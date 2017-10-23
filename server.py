import asyncio
import logging
from protocodecs import SimpleJsonCodec

logging.basicConfig()
logger = logging.getLogger("pycortex")
logger.setLevel(logging.INFO)

DEFAULT_TIMEOUT = 3600
MAX_TIMEOUT = 86400

"""
Protocol:
SET:
3:SET,<netstring:key><netstring:value>[<netstring:timeout in seconds>]

GET:
3:GET,<netstring:key>
Returns
<netstring:data>
"""

cache = {}

class Entry:
    def __init__(self):
        self._value = None
        self._timeout = None

class Server(asyncio.Protocol):
    def __init__(self, codec):
        self._codec = codec
        self._transport = None

    def connection_made(self, transport):
        pass
        self._transport = transport

    def connection_lost(self, reason):
        pass

    def data_received(self, data):
        request = self._codec.decode_request(data)
        if request.method == "GET":
            try:
                value = cache[request.key]
            except KeyError:
                # Cache miss
                self._transport.write(self._codec.encode_response(None, True))
            else:
                # Cache hit
                self._transport.write(self._codec.encode_response(value, False))
        elif request.method == "SET":
            cache[request.key] = request.value
            self._transport.write(self._codec.encode_response(None, False))
        else:
            logger.warning('Unknown method "%s" from client' % (request.method))


def start(loop, codec, host='0.0.0.0', port=1234):

    def server_factory(codec):
        def create():
            return Server(codec)
            #return Dummy()
        return create

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
