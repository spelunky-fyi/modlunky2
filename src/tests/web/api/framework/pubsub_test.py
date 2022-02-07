from dataclasses import dataclass
from starlette.applications import Starlette
from starlette.testclient import TestClient, WebSocketTestSession
from typing import Any, Generator, Type, TypeVar
import pytest
from serde import serde

from modlunky2.web.api.framework.multiplexing import (
    SendConnection,
    WSMultiplexer,
    WSMultiplexerRoute,
)
from modlunky2.web.api.framework.pubsub import (
    PubSubManager,
    PubSubTopic,
    Published,
    ServiceLevel,
    Subscribe,
)
from modlunky2.web.api.framework.serde_tag import (
    TagDeserializer,
    TaggedMessage,
    to_tagged_dict,
)


@serde
@dataclass
class Echo:
    msg: str


@serde
@dataclass
class Broadcast:
    announcement: str


@serde
@dataclass
class Notice:
    message: str


@dataclass
class Broadcaster:
    manager: PubSubManager

    async def handler(self, _connection: SendConnection, req: Broadcast) -> None:
        self.manager.publish(Notice(req.announcement))


async def echo_handler(connection: SendConnection, req: Echo) -> None:
    await connection.send(req)


@pytest.fixture(name="tag_de")
def make_tag_de() -> TagDeserializer:
    return TagDeserializer([Echo, Notice, Published])


@pytest.fixture(name="client")
def make_client() -> Generator[TestClient, None, None]:
    manager = PubSubManager([PubSubTopic(Notice, ServiceLevel.MUST_DELIVER)])

    broadcaster = Broadcaster(manager)
    multiplexer = WSMultiplexer(
        (
            WSMultiplexerRoute[Broadcast](Broadcast, broadcaster.handler),
            WSMultiplexerRoute[Echo](Echo, echo_handler),
        )
        + manager.multiplexer_routes
    )

    app = Starlette(routes=[multiplexer.starlette_route])
    test_client = TestClient(app=app)
    with test_client:
        yield test_client


def test_not_subscribed(client: TestClient):
    connection: WebSocketTestSession = client.websocket_connect("/123")
    with connection:
        connection.send_json(to_tagged_dict(Broadcast("not listening")))
        # When the connection context exits, it asserts there are no messages in its queue


T = TypeVar("T")


def from_published(tag_de: TagDeserializer, data: Any, typ: Type[T]) -> T:
    pub = tag_de.from_tagged_dict(data)
    assert isinstance(pub, Published)

    msg = tag_de.from_tagged_dict(TaggedMessage(pub.message))
    assert isinstance(msg, typ)
    return msg


def test_one_subscribed(
    client: TestClient,
    tag_de: TagDeserializer,
):
    connection: WebSocketTestSession = client.websocket_connect("/123")
    with connection:
        connection.send_json(to_tagged_dict(Subscribe({Notice.__name__})))

        to_send = "listen up"
        connection.send_json(to_tagged_dict(Broadcast(to_send)))

        data = connection.receive_json()
        got_msg = from_published(tag_de, data, Notice)
        assert got_msg == Notice(to_send)


def test_two_subscribed(
    client: TestClient,
    tag_de: TagDeserializer,
):
    c1: WebSocketTestSession = client.websocket_connect("/123")
    c2: WebSocketTestSession = client.websocket_connect("/456")
    with c1:
        with c2:
            c1.send_json(to_tagged_dict(Subscribe({Notice.__name__})))
            c2.send_json(to_tagged_dict(Subscribe({Notice.__name__})))

            # WebSocketTestSession.send_json() doesn't wait for the message to be processed before returning.
            # So, we use echos to ensure both Subscribe requests have been processed.
            echo1 = to_tagged_dict(Echo("yo"))
            c1.send_json(echo1)
            assert c1.receive_json() == echo1

            echo2 = to_tagged_dict(Echo("hi"))
            c2.send_json(echo2)
            assert c2.receive_json() == echo2

            # Make the publish event happen
            to_send = "you two"
            c2.send_json(to_tagged_dict(Broadcast(to_send)))

            data1 = c1.receive_json()
            got1 = from_published(tag_de, data1, Notice)
            assert got1 == Notice(to_send)

            data2 = c2.receive_json()
            got2 = from_published(tag_de, data2, Notice)
            assert got2 == Notice(to_send)

        # Try publishing after a client disconnected
        to_send = "just us"
        c1.send_json(to_tagged_dict(Broadcast(to_send)))

        data3 = c1.receive_json()
        got3 = from_published(tag_de, data3, Notice)
        assert got3 == Notice(to_send)
