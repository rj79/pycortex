# About
Pycortex is a very simple caching server. It can store string key/value
pairs. Both the server and the client library is built using asyncio.

# Protocol details
* Requests and responses are sent as JSON.
* Keys must be alphanumeric
* Values are utf-8.

## Requests to server
* Set: {"m": "SET", "k": <key>, "v": <value>}
* Get: {"m": "GET", "k": <key>}
* Evict: {"m": "EVICT", "k": <key>}
* Clear: {"m": "CLEAR"}

## Responses from server
* Cache hit (Get): {"v": <value>, "e": False}
* Error (Get, Evict): {"v": None, "e": True}
* Ack (Set, Evict, Clear): {"v": None, "e": False}
