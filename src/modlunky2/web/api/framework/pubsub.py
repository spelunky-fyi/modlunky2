from __future__ import annotations
import dataclasses
from enum import Enum, auto
import logging
import math
from anyio import (
    TASK_STATUS_IGNORED,
    WouldBlock,
    create_memory_object_stream,
    create_task_group,
)
from anyio.abc import TaskStatus
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from dataclasses import InitVar, dataclass
from serde import serde
from typing import (
    Any,
    Dict,
    Iterable,
    Set,
    Tuple,
    Type,
)


from modlunky2.web.api.framework.multiplexing import SendConnection, WSMultiplexerRoute
from modlunky2.web.api.framework.serde_tag import to_tagged_dict
from modlunky2.web.api.framework.session import SessionId

logger = logging.getLogger(__name__)


@serde
@dataclass(frozen=True)
class Subscribe:
    topics: Set[str]


@serde
@dataclass(frozen=True)
class Unsubscribe:
    topics: Set[str]


@serde
@dataclass(frozen=True)
class Published:
    # Should be TaggedMessage, but I'm unsure how to use pyserde with it
    message: Dict[str, Any]


class ServiceLevel(Enum):
    MUST_DELIVER = auto()
    MAY_DROP = auto()


@dataclass(frozen=True)
class PubSubTopic:
    typ: Type[Any]
    service_level: ServiceLevel


@dataclass
class _TopicInfo:
    service_level: ServiceLevel
    subscribers: Set[SessionId] = dataclasses.field(default_factory=set)


@dataclass
class _StreamPair:
    max_buffer_size: InitVar[float]

    send: MemoryObjectSendStream[Published] = dataclasses.field(init=False)
    recv: MemoryObjectReceiveStream[Published] = dataclasses.field(init=False)

    def __post_init__(self, max_buffer_size: float):
        self.send, self.recv = create_memory_object_stream(max_buffer_size, Published)


@dataclass
class _SessionCopier:
    connection: SendConnection

    _may_drop: _StreamPair = dataclasses.field(init=False)
    _must_deliver: _StreamPair = dataclasses.field(init=False)

    def __post_init__(self):
        self._may_drop = _StreamPair(0)
        self._must_deliver = _StreamPair(math.inf)

    def send(self, level: ServiceLevel, pub: Published):
        if level is ServiceLevel.MAY_DROP:
            stream = self._may_drop.send
        elif level is ServiceLevel.MUST_DELIVER:
            stream = self._must_deliver.send
        else:
            raise ValueError(f"Unknown service level {level}")  # pragma: no cover

        try:
            stream.send_nowait(pub)
        except WouldBlock:
            pass

    async def run(
        self,
        *,
        task_status: TaskStatus = TASK_STATUS_IGNORED,
    ) -> None:
        """Send messages until the client disconnects"""
        async with self._may_drop.recv, self._must_deliver.recv, create_task_group() as tg:
            await tg.start(self._run_one, self._may_drop.recv)
            await tg.start(self._run_one, self._must_deliver.recv)
            task_status.started()

    async def _run_one(
        self,
        recv: MemoryObjectReceiveStream[Published],
        *,
        task_status: TaskStatus = TASK_STATUS_IGNORED,
    ) -> None:
        task_status.started()
        async for pub in recv:
            await self.connection.send(pub)


@dataclass
class PubSubManager:
    topics: InitVar[Iterable[PubSubTopic]]

    _topic_info: Dict[str, _TopicInfo] = dataclasses.field(
        init=False, default_factory=dict
    )
    _sessions: Dict[SessionId, _SessionCopier] = dataclasses.field(
        init=False, default_factory=dict
    )

    def __post_init__(self, topics: Iterable[PubSubTopic]):
        for t in topics:
            name = t.typ.__name__
            if name in self._topic_info:
                raise ValueError(f"Topic {name} appears more than once")
            self._topic_info[name] = _TopicInfo(t.service_level)

    @property
    def multiplexer_routes(self) -> Tuple[WSMultiplexerRoute[Any], ...]:
        return (
            WSMultiplexerRoute(Subscribe, self._subscribe),
            WSMultiplexerRoute(Unsubscribe, self._unsubscribe),
        )

    def publish(self, msg: Any):
        topic_name = type(msg).__name__
        if topic_name not in self._topic_info:
            raise ValueError(f"Topic {topic_name} is unknown")
        info = self._topic_info[topic_name]
        pub = Published(to_tagged_dict(msg))
        for sid in info.subscribers:
            self._sessions[sid].send(info.service_level, pub)

    async def _subscribe(self, connection: SendConnection, req: Subscribe) -> None:
        self._check_topics(req.topics)
        self._maybe_add_session(connection)
        for topic in req.topics:
            self._topic_info[topic].subscribers.add(connection.session_id)

    async def _unsubscribe(self, connection: SendConnection, req: Unsubscribe) -> None:
        self._check_topics(req.topics)
        for topic in req.topics:
            self._topic_info[topic].subscribers.discard(connection.session_id)

    def _check_topics(self, raw_topics: Set[str]) -> None:
        unknown_topics: Set[str] = set()
        for t in raw_topics:
            if t not in self._topic_info:
                unknown_topics.add(t)
        if unknown_topics:
            raise ValueError(f"Request contains unknown topics {unknown_topics!r}")

    def _maybe_add_session(self, connection: SendConnection):
        if connection.session_id in self._sessions:
            return
        self._sessions[connection.session_id] = _SessionCopier(connection)
        connection.task_group.start_soon(
            self._run_session,
            connection.session_id,
            name=f"pubsub copier for sid {connection.session_id}",
        )

    async def _run_session(self, session_id: SessionId):
        try:
            await self._sessions[session_id].run()
        finally:
            # Cleanup the session
            for ti in self._topic_info.values():
                ti.subscribers.discard(session_id)
            del self._sessions[session_id]
