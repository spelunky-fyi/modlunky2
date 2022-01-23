from contextlib import contextmanager
from dataclasses import dataclass, field
import logging
from starlette.datastructures import Address
from starlette.websockets import WebSocket
from typing import Dict, Generator, NewType

logger = logging.getLogger("modlunky2")

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
        if sid in self.sid_to_addr and self.sid_to_addr[sid] != addr:
            logger.warning(
                "Session %s already in use by %r, attempted reuse by %r",
                sid,
                self.sid_to_addr[sid],
                addr,
            )
            raise SessionException(
                f"Session ID {sid} is already used by another client"
            )
        self.sid_to_addr[sid] = addr

        yield sid

        del self.sid_to_addr[sid]
