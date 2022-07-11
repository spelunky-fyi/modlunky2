from anyio import create_task_group
from anyio.abc import TaskGroup
from dataclasses import dataclass
import logging
from starlette.routing import WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    Iterable,
    Type,
    TypeVar,
)

from modlunky2.web.api.framework.serde_tag import (
    TagException,
    TagDeserializer,
    TaggedMessage,
    to_tagged_dict,
)
from modlunky2.web.api.framework.session import (
    SessionException,
    SessionId,
    SessionManager,
)

logger = logging.getLogger(__name__)

ParamType = TypeVar("ParamType")


class SendConnection:
    def __init__(
        self, websocket: WebSocket, session_id: SessionId, task_group: TaskGroup
    ) -> None:
        self._websocket = websocket
        self._session_id = session_id
        self._task_group = task_group

    @property
    def session_id(self) -> SessionId:
        return self._session_id

    @property
    def task_group(self) -> TaskGroup:
        return self._task_group

    async def send(self, obj: Any) -> None:
        data = to_tagged_dict(obj)
        await self._websocket.send_json(data)


MultiplexerEndpoint = Callable[[SendConnection, ParamType], Awaitable[None]]


@dataclass(frozen=True)
class WSMultiplexerRoute(Generic[ParamType]):
    param_type: Type[ParamType]
    endpoint: MultiplexerEndpoint[ParamType]


class WSMultiplexer:
    def __init__(self, routes: Iterable[WSMultiplexerRoute[Any]]) -> None:
        self._param_to_endpoint: Dict[Type[Any], MultiplexerEndpoint[Any]] = {}
        for r in routes:
            self._param_to_endpoint[r.param_type] = r.endpoint

        self._param_deserializer = TagDeserializer(self._param_to_endpoint.keys())
        self._sid_manager = SessionManager("ws_session_id")
        self._route = WebSocketRoute("/{ws_session_id}", self._endpoint)

    @property
    def starlette_route(self) -> WebSocketRoute:
        return self._route

    async def _endpoint(self, websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            with self._sid_manager.session_for(websocket) as session_id:
                async with create_task_group() as tg:
                    while True:
                        await self._dispatch_one(websocket, session_id, tg)
        except SessionException as ex:
            logger.warning("Rejected websocket session", exc_info=ex)
            await websocket.close(reason=str(ex))
        except WebSocketDisconnect:
            # We swallow disconnect since it's OK for clients to close the connection.
            # We don't swallow close since we don't (currently) expect handlers to close the connection.
            pass

    async def _dispatch_one(
        self, websocket: WebSocket, session_id: SessionId, task_group: TaskGroup
    ) -> None:
        data: TaggedMessage = await websocket.receive_json()
        try:
            obj = self._param_deserializer.from_tagged_dict(data)
        except (TagException, TypeError) as ex:
            logger.warning("Deserializing request failed %s", ex)
            return

        endpoint = self._param_to_endpoint[type(obj)]
        sender = SendConnection(websocket, session_id, task_group)

        await endpoint(sender, obj)
