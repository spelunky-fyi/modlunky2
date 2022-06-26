from contextlib import contextmanager
from dataclasses import dataclass, field
import logging
from starlette.datastructures import Address
from starlette.websockets import WebSocket
from typing import Dict, Generator, NewType

logger = logging.getLogger(__name__)

SessionId = NewType("SessionId", str)


class SessionException(Exception):
    pass


@dataclass
class SessionManager:
    route_sid_param_name: str
    sid_to_addr: Dict[SessionId, Address] = field(default_factory=dict)

    @contextmanager
    def session_for(self, websocket: WebSocket) -> Generator[SessionId, None, None]:
        sid = SessionId(websocket.path_params[self.route_sid_param_name])
        addr = websocket.client

        if sid in self.sid_to_addr:
            logger.warning(
                "Session %s already in use by %r, attempted reuse by %r",
                sid,
                self.sid_to_addr[sid],
                addr,
            )
            raise SessionException(
                f"Session ID {sid} is currently being used by another connection"
            )
        self.sid_to_addr[sid] = addr

        try:
            yield sid
        finally:
            del self.sid_to_addr[sid]
