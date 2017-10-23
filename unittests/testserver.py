import unittest
import server
import protocodecs

class MockTransport:
    def __init__(self):
        self._response = None

    def write(self, data):
        self._response = data

    def read(self):
        return self._response

class TestServer(unittest.TestCase):
    def setUp(self):
        server.clear_cache()
        self.transport = MockTransport()
        self.codec = protocodecs.SimpleJsonCodec()
        self.server = server.Server(self.codec)
        self.server.connection_made(self.transport)

    def test_get_uncached_key_returns_miss(self):
        self.server.data_received(self.codec.encode_get("foo"))

        response = self.codec.decode_response(self.transport.read())
        self.assertTrue(response.error)
        self.assertEqual(None, response.value)

    def test_set_value_gives_ack(self):
        self.server.data_received(self.codec.encode_set("foo", "bar"))

        response = self.codec.decode_response(self.transport.read())
        self.assertFalse(response.error)
        self.assertEqual(None, response.value)

    def test_get_after_set_returns_value(self):
        self.server.data_received(self.codec.encode_set("foo", "bar"))
        self.server.data_received(self.codec.encode_get("foo"))

        response = self.codec.decode_response(self.transport.read())
        self.assertFalse(response.error)
        self.assertEqual("bar", response.value)

    def test_server_objects_share_cache(self):
        # Set up another server object in addition to the one in setUp
        transport = MockTransport()
        codec = protocodecs.SimpleJsonCodec()
        srv = server.Server(codec)
        srv.connection_made(transport)

        # Execute
        self.server.data_received(self.codec.encode_set("foo", "bar"))
        srv.data_received(codec.encode_get("foo"))

        # Verify
        response = codec.decode_response(transport.read())
        self.assertFalse(response.error)
        self.assertEqual("bar", response.value)

    def test_no_response_if_unknown_method(self):
        self.server.data_received(b'{"m":"hack", "k":"attempt"}')
        self.assertEqual(None, self.transport.read())
