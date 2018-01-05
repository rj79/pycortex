import asyncio
from protocodecs import SimpleJsonCodec
import sys

def connection(host, port):
    return ClientContext(host, port)

class ClientContext:
    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._client = None

    def __enter__(self):
        self._client = connect(self._host, self._port)
        return self._client

    def __exit__(self, type, value, traceback):
        self._client.close()

class Client(asyncio.Protocol):
    def __init__(self, loop, codec):
        self._loop = loop
        self._codec = codec
        self._transport = None
        self._request = None

    def connection_made(self, transport):
        self._transport = transport

    def close(self):
        if self._transport is not None:
            self._transport.close()

    def connection_lost(self, reason):
        if self._request:
            self._request.cancel()

    def data_received(self, data):
        self._request.set_result(self._codec.decode_response(data))

    def set(self, key, value):
        self._transport.write(self._codec.encode_set(key, value))
        self._request = asyncio.Future()
        asyncio.ensure_future(self._request)
        self._loop.run_until_complete(self._request)

    def get(self, key):
        self._transport.write(self._codec.encode_get(key))
        self._request = asyncio.Future()
        asyncio.ensure_future(self._request)
        self._loop.run_until_complete(self._request)
        result = self._request.result()
        if result.is_hit():
            return result.value
        raise KeyError('Key "%s" not found' % (key))

    def evict(self, key):
        self._transport.write(self._codec.encode_evict(key))
        self._request = asyncio.Future()
        asyncio.ensure_future(self._request)
        self._loop.run_until_complete(self._request)
        result = self._request.result()
        if result.is_error():
            raise KeyError('Key "%s" not found' % (key))

    def clear(self):
        self._transport.write(self._codec.encode_clear())
        self._request = asyncio.Future()
        asyncio.ensure_future(self._request)
        self._loop.run_until_complete(self._request)


def client_factory(loop, codec):
    def create():
        return Client(loop, codec)
    return create

def connect(host, port):
    loop = asyncio.get_event_loop()
    codec = SimpleJsonCodec()

    connect_coro = loop.create_connection(client_factory(loop, codec), host,
                                          port)

    try:
        transport, client = loop.run_until_complete(connect_coro)
    except ConnectionRefusedError:
        print("Connection refused")
        return None
    return client

def print_usage():
    print("Usage: client set <key> <value>")
    print("       client get <key>")
    print("       client evict <key>")
    print("       client clear")

def main(args):
    client = connect('127.0.0.1', 1234)
    if not client:
        return False

    if len(args) < 1:
        print_usage()
        return False

    cmd = args[0]
    if cmd == "set":
        if len(args) < 3:
            print_usage()
            return False
        key = args[1]
        value = args[2]
        client.set(key, value)
    elif cmd == "get":
        if len(args) < 2:
            print_usage()
            return False
        key = args[1]
        try:
            print(client.get(key))
        except KeyError:
            pass
    elif cmd == "evict":
        if len(args) < 2:
            print_usage()
            return False
        key = args[1]
        try:
            client.evict(key)
        except KeyError:
            pass
    elif cmd == "clear":
        client.clear()
    else:
        print('Unknown command %s' % (cmd))
        return False
    return True


if __name__ == '__main__':
    if not main(sys.argv[1:]):
        sys.exit(1)
