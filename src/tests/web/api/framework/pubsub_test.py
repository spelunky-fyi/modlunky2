from dataclasses import dataclass
from starlette.applications import Starlette
from starlette.testclient import TestClient, WebSocketTestSession
from typing import Generator
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


@pytest.fixture(name="tag_de")
def make_tag_de() -> TagDeserializer:
    return TagDeserializer([Notice, Published])


@pytest.fixture(name="client")
def make_client() -> Generator[TestClient, None, None]:
    manager = PubSubManager([PubSubTopic(Notice, ServiceLevel.MUST_DELIVER)])

    broadcaster = Broadcaster(manager)
    multiplexer = WSMultiplexer(
        (WSMultiplexerRoute[Broadcast](Broadcast, broadcaster.handler),)
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
        got_pub = tag_de.from_tagged_dict(data)
        assert isinstance(got_pub, Published)

        got_msg = tag_de.from_tagged_dict(TaggedMessage(got_pub.message))
        assert got_msg == Notice(to_send)
