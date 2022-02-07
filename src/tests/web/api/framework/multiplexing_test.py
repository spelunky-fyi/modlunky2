from dataclasses import dataclass
from typing import Generator
import pytest
from serde import serde
from starlette.applications import Starlette
from starlette.testclient import TestClient, WebSocketTestSession
from starlette.websockets import WebSocketDisconnect

from modlunky2.web.api.framework.multiplexing import (
    SendConnection,
    WSMultiplexer,
    WSMultiplexerRoute,
)


@serde
@dataclass
class Person:
    name: str


@serde
@dataclass
class Greeting:
    phrase: str


async def hello(connection: SendConnection, person: Person):
    await connection.send(Greeting(f"hi {person.name} from {connection.session_id}"))


@pytest.fixture(name="client")
def make_client() -> Generator[TestClient, None, None]:
    multiplexer = WSMultiplexer([WSMultiplexerRoute[Person](Person, hello)])
    app = Starlette(routes=[multiplexer.starlette_route])
    test_client = TestClient(app=app)
    with test_client:
        yield test_client


def test_requests(client: TestClient):
    connection: WebSocketTestSession = client.websocket_connect("/123")
    with connection:
        connection.send_json({"Person": {"name": "Ana"}})
        assert connection.receive_json() == {"Greeting": {"phrase": "hi Ana from 123"}}

        connection.send_json({"Person": {"name": "Terra"}})
        assert connection.receive_json() == {
            "Greeting": {"phrase": "hi Terra from 123"}
        }


def test_duplicate_session(client: TestClient):
    connection1: WebSocketTestSession = client.websocket_connect("/456")
    connection2: WebSocketTestSession = client.websocket_connect("/456")
    with connection1, connection2:
        with pytest.raises(WebSocketDisconnect, match=r"ID 456"):
            connection2.receive_json()


def test_skip_unrecognized(client: TestClient):
    connection: WebSocketTestSession = client.websocket_connect("/789")
    with connection:
        connection.send_json({"Mysterious": {}})
        connection.send_json({"Person": {"name": "Tina"}})
        assert connection.receive_json() == {"Greeting": {"phrase": "hi Tina from 789"}}
