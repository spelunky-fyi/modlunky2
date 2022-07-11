from contextlib import contextmanager
from dataclasses import dataclass, field
import logging
from starlette.datastructures import Address
from starlette.websockets import WebSocket
from typing import Dict, Generator, NewType
from urllib.parse import urlsplit

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
        # If there's no origin, this isn't a browser request.
        # We assume it's from a local process and allow it.
        if "origin" in websocket.headers:
            _validate_origin(websocket.headers["origin"])

        sid = SessionId(websocket.path_params[self.route_sid_param_name])
        addr = websocket.client
        if addr is None:
            raise SessionException(f"Session {sid} has no client address")

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


# Allow the most common localhost 'spellings.' This doesn't bother with
# supporting alternative IPv4 loopbacks (e.g. 127.0.0.2). Notably IPv6 gets
# canonicalized elsewhere; we'll never see (e.g.) "[0:0:0:0:0:0:000:1]"
_ALLOWED_ORIGINS = frozenset(["localhost", "127.0.0.1", "[::1]"])


def _validate_origin(origin: str) -> None:
    # It might be nice to allow file: scheme, but we'd also have to allow the others.
    # Unfortunately, it's possible to construct (e.g.) a data: URL from any origin
    if origin == "null":
        raise SessionException(
            "Connection from privacy-sensitive origin (e.g. file:, data:)"
        )

    try:
        parsed = urlsplit(origin)
    except ValueError as err:
        raise SessionException("Failed to parse origin") from err

    hostname = _extract_hostname(parsed.netloc)
    if hostname not in _ALLOWED_ORIGINS:
        raise SessionException(f"Unauthorized hostname ({hostname}) in origin {origin}")


def _extract_hostname(netloc: str) -> str:
    # Try to ignore the port. For IPv6 addresses, there may be ":" in the address
    colon_index = netloc.rfind(":")
    close_index = netloc.rfind("]")
    if colon_index < 0:
        return netloc
    if close_index >= 0 and close_index > colon_index:
        return netloc
    if colon_index < 0:
        return netloc
    return netloc[0:colon_index]
