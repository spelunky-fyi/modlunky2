from contextlib import asynccontextmanager
from anyio import create_memory_object_stream, create_task_group
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from dataclasses import dataclass
from starlette.applications import Starlette
from starlette.testclient import TestClient, WebSocketTestSession
from typing import Any, Generator, Type, TypeVar, cast
import pytest
from serde import serde

from modlunky2.web.api.framework.multiplexing import (
    SendConnection,
    WSMultiplexer,
    WSMultiplexerRoute,
)
from modlunky2.web.api.framework.pubsub import (
    _SessionCopier,
    PubSubManager,
    PubSubTopic,
    Published,
    ServiceLevel,
    Subscribe,
    Unsubscribe,
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


T = TypeVar("T")


def from_published(tag_de: TagDeserializer, data: Any, typ: Type[T]) -> T:
    pub = tag_de.from_tagged_dict(data)
    assert isinstance(pub, Published)

    msg = tag_de.from_tagged_dict(TaggedMessage(pub.message))
    assert isinstance(msg, typ)
    return msg


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


def test_one_subscribed(client: TestClient, tag_de: TagDeserializer):
    connection: WebSocketTestSession = client.websocket_connect("/123")
    with connection:
        connection.send_json(to_tagged_dict(Subscribe({Notice.__name__})))

        to_send = "listen up"
        connection.send_json(to_tagged_dict(Broadcast(to_send)))

        data = connection.receive_json()
        got_msg = from_published(tag_de, data, Notice)
        assert got_msg == Notice(to_send)


def test_one_subscribed_duplicate(client: TestClient, tag_de: TagDeserializer):
    connection: WebSocketTestSession = client.websocket_connect("/123")
    with connection:
        connection.send_json(to_tagged_dict(Subscribe({Notice.__name__})))
        # This duplication should be OK
        connection.send_json(to_tagged_dict(Subscribe({Notice.__name__})))

        to_send = "still ok"
        connection.send_json(to_tagged_dict(Broadcast(to_send)))

        data = connection.receive_json()
        got_msg = from_published(tag_de, data, Notice)
        assert got_msg == Notice(to_send)


def test_unsubscribe_wo_sub(client: TestClient):
    connection: WebSocketTestSession = client.websocket_connect("/123")
    with connection:
        connection.send_json(to_tagged_dict(Unsubscribe({Notice.__name__})))
        connection.send_json(to_tagged_dict(Broadcast("can't hear this")))


def test_unsubscribe_after_sub(client: TestClient):
    connection: WebSocketTestSession = client.websocket_connect("/123")
    with connection:
        connection.send_json(to_tagged_dict(Subscribe({Notice.__name__})))
        connection.send_json(to_tagged_dict(Unsubscribe({Notice.__name__})))
        connection.send_json(to_tagged_dict(Broadcast("not heard")))


def test_two_subscribed(client: TestClient, tag_de: TagDeserializer):
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


@pytest.mark.parametrize("to_send", [Subscribe({"bogus"}), Unsubscribe({"bad"})])
def test_subscribe_unknown(client: TestClient, to_send: Any):
    with client:
        connection: WebSocketTestSession = client.websocket_connect("/123")
        with pytest.raises(ValueError, match=r"unknown topics"), connection:
            connection.send_json(to_tagged_dict(to_send))
            # This ensures we wait for the exception
            connection.receive_json()


def test_duplicate_topic_name():
    topics = [
        PubSubTopic(Notice, ServiceLevel.MAY_DROP),
        PubSubTopic(Notice, ServiceLevel.MUST_DELIVER),
    ]
    with pytest.raises(ValueError, match=r"more than once"):
        PubSubManager(topics)


def test_publish_unknown():
    pub_manager = PubSubManager([PubSubTopic(Notice, ServiceLevel.MUST_DELIVER)])
    with pytest.raises(ValueError, match=r"unknown"):
        pub_manager.publish(Broadcast("shouldn't work"))


@dataclass
class FakeSendConnection:
    _send: MemoryObjectSendStream[Published]

    async def send(self, pub: Published):
        await self._send.send(pub)


@dataclass
class CopierFixture:
    copier: _SessionCopier
    receive: MemoryObjectReceiveStream[Published]


@asynccontextmanager
async def make_copier_fixture():
    # Note: We use a context manager to safely manage the task group

    send, receive = create_memory_object_stream(1, Published)
    connection = cast(SendConnection, FakeSendConnection(send))
    copier = _SessionCopier(connection)

    async with send, receive, create_task_group() as tg:
        await tg.start(copier.run)

        yield CopierFixture(copier, receive)

        # Stop the copier
        tg.cancel_scope.cancel()

    # Make sure there's nothing left in the stream
    assert receive.statistics().current_buffer_used == 0


@pytest.mark.anyio
async def test_copier_must_deliver():
    async with make_copier_fixture() as fix:
        fix.copier.send(ServiceLevel.MUST_DELIVER, Published({"started": True}))
        assert await fix.receive.receive() == Published({"started": True})


@pytest.mark.anyio
async def test_copier_may_drop():
    async with make_copier_fixture() as fix:
        fix.copier.send(ServiceLevel.MAY_DROP, Published({"kept": True}))
        assert await fix.receive.receive() == Published({"kept": True})


@pytest.mark.anyio
async def test_copier_priority_case1():
    async with make_copier_fixture() as fix:
        fix.copier.send(ServiceLevel.MUST_DELIVER, Published({"clogging": True}))
        fix.copier.send(ServiceLevel.MAY_DROP, Published({"buffered": True}))
        fix.copier.send(ServiceLevel.MUST_DELIVER, Published({"must_keep": True}))
        for k in ["clogging", "buffered", "must_keep"]:
            assert await fix.receive.receive() == Published({k: True})


@pytest.mark.anyio
async def test_copier_priority_case2():
    async with make_copier_fixture() as fix:
        fix.copier.send(ServiceLevel.MAY_DROP, Published({"clogging": True}))
        fix.copier.send(ServiceLevel.MAY_DROP, Published({"dropped": True}))
        fix.copier.send(ServiceLevel.MUST_DELIVER, Published({"must_keep_1": True}))
        fix.copier.send(ServiceLevel.MUST_DELIVER, Published({"must_keep_2": True}))
        for k in ["clogging", "must_keep_1", "must_keep_2"]:
            assert await fix.receive.receive() == Published({k: True})
