import unittest
import server
import os
import protocodecs
import time
import logging

server.logger.setLevel(logging.CRITICAL)

class MockTimeSource:
    def __init__(self):
        self.time = 0

    def get_time(self):
        return self.time

    def advance(self):
        self.time += 1

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

    def test_01_get_uncached_key_returns_miss(self):
        self.server.data_received(self.codec.encode_get("foo"))

        response = self.codec.decode_response(self.transport.read())
        self.assertTrue(response.error)
        self.assertEqual(None, response.value)

    def test_02_set_value_gives_ack(self):
        self.server.data_received(self.codec.encode_set("foo", "bar"))

        response = self.codec.decode_response(self.transport.read())
        self.assertFalse(response.error)
        self.assertEqual(None, response.value)

    def test_03_get_after_set_returns_value(self):
        self.server.data_received(self.codec.encode_set("foo", "bar"))
        self.server.data_received(self.codec.encode_get("foo"))

        response = self.codec.decode_response(self.transport.read())
        self.assertFalse(response.error)
        self.assertEqual("bar", response.value)

    def test_04_server_objects_share_cache(self):
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

    def test_05_no_response_if_unknown_method(self):
        self.server.data_received(b'{"m":"hack", "k":"attempt"}')
        self.assertEqual(None, self.transport.read())

    def test_06_remove_oldest_entry_when_entry_limit_reached(self):
        self.server.set_entry_limit(2)
        time_source = MockTimeSource()
        server._time_source = time_source

        self.server.data_received(self.codec.encode_set("key1", "value1"))
        time_source.advance()
        self.server.data_received(self.codec.encode_set("key2", "value2"))
        time_source.advance()
        # This should push key1 out of the cache since the limit is reached
        self.server.data_received(self.codec.encode_set("key3", "value3"))
        self.server.data_received(self.codec.encode_get("key1"))
        response1 = self.codec.decode_response(self.transport.read())
        self.server.data_received(self.codec.encode_get("key2"))
        response2 = self.codec.decode_response(self.transport.read())
        self.server.data_received(self.codec.encode_get("key3"))
        response3 = self.codec.decode_response(self.transport.read())

        self.assertTrue(response1.error)
        self.assertEqual(None, response1.value)

        self.assertFalse(response2.error)
        self.assertEqual("value2", response2.value)

        self.assertFalse(response3.error)
        self.assertEqual("value3", response3.value)

    def test_07_get_updates_last_access_time(self):
        self.server.set_entry_limit(2)
        time_source = MockTimeSource()
        server._time_source = time_source

        self.server.data_received(self.codec.encode_set("key1", "value1"))
        time_source.advance()
        self.server.data_received(self.codec.encode_set("key2", "value2"))
        # Accessing key1 makes key2 the oldest accessed
        time_source.advance()
        self.server.data_received(self.codec.encode_get("key1"))
        time_source.advance()
        # This should push key2 out of the cache
        self.server.data_received(self.codec.encode_set("key3", "value3"))

        self.server.data_received(self.codec.encode_get("key1"))
        response1 = self.codec.decode_response(self.transport.read())
        self.server.data_received(self.codec.encode_get("key2"))
        response2 = self.codec.decode_response(self.transport.read())
        self.server.data_received(self.codec.encode_get("key3"))
        response3 = self.codec.decode_response(self.transport.read())

        self.assertFalse(response1.error)
        self.assertEqual("value1", response1.value)

        self.assertTrue(response2.error)
        self.assertEqual(None, response2.value)

        self.assertFalse(response3.error)
        self.assertEqual("value3", response3.value)

    def test_08_evict_non_existing_returns_error(self):
        self.server.data_received(self.codec.encode_evict("foo"))

        response = self.codec.decode_response(self.transport.read())
        self.assertTrue(response.error)
        self.assertEqual(None, response.value)

    def test_09_get_key_returns_miss_after_evict(self):
        self.server.data_received(self.codec.encode_set("foo", "bar"))
        self.server.data_received(self.codec.encode_evict("foo"))

        response = self.codec.decode_response(self.transport.read())
        self.assertFalse(response.error)
        self.assertEqual(None, response.value)

        self.server.data_received(self.codec.encode_get("foo"))

        response = self.codec.decode_response(self.transport.read())
        self.assertTrue(response.error)
        self.assertEqual(None, response.value)

    def test_10_no_values_after_clear(self):
        self.server.data_received(self.codec.encode_set("foo", "bar"))
        self.server.data_received(self.codec.encode_set("baz", "zok"))
        self.server.data_received(self.codec.encode_clear())

        response = self.codec.decode_response(self.transport.read())
        self.assertFalse(response.error)
        self.assertEqual(None, response.value)

        self.server.data_received(self.codec.encode_get("foo"))
        response = self.codec.decode_response(self.transport.read())
        self.assertTrue(response.error)
        self.assertEqual(None, response.value)

        self.server.data_received(self.codec.encode_get("baz"))
        response = self.codec.decode_response(self.transport.read())
        self.assertTrue(response.error)
        self.assertEqual(None, response.value)

    def test_11_can_set_entry_limit_with_environment_varialbe(self):
        os.environ['PYCORTEX_ENTRY_LIMIT'] = '2'

        # Re-create server so that environment variable can be taken into
        # account
        self.server = server.Server(self.codec)
        self.server.connection_made(self.transport)

        time_source = MockTimeSource()
        server._time_source = time_source

        self.server.data_received(self.codec.encode_set("key1", "value1"))
        time_source.advance()
        self.server.data_received(self.codec.encode_set("key2", "value2"))
        time_source.advance()
        # This should push key1 out of the cache since the limit is reached
        self.server.data_received(self.codec.encode_set("key3", "value3"))
        self.server.data_received(self.codec.encode_get("key1"))
        response1 = self.codec.decode_response(self.transport.read())
        self.server.data_received(self.codec.encode_get("key2"))
        response2 = self.codec.decode_response(self.transport.read())
        self.server.data_received(self.codec.encode_get("key3"))
        response3 = self.codec.decode_response(self.transport.read())

        self.assertTrue(response1.error)
        self.assertEqual(None, response1.value)

        self.assertFalse(response2.error)
        self.assertEqual("value2", response2.value)

        self.assertFalse(response3.error)
        self.assertEqual("value3", response3.value)

    def test_12_no_crash_if_environment_variable_invalid(self):
        os.environ['PYCORTEX_ENTRY_LIMIT'] = 'not_an_integer'

        # Re-create server so that environment variable can be taken into
        # account
        try:
            self.server = server.Server(self.codec)
        except:
            self.assertFalse(True)
