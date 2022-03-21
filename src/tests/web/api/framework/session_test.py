from dataclasses import dataclass
import pytest
from starlette.datastructures import Address
from starlette.websockets import WebSocket, WebSocketDisconnect
from typing import Dict, cast

from modlunky2.web.api.framework.session import (
    SessionException,
    SessionId,
    SessionManager,
)


@dataclass
class FakeWebSocket:
    path_params: Dict[str, str]
    client: Address


PARAM_NAME = "sid"


@pytest.mark.parametrize("sid", [SessionId("123"), SessionId("abc")])
def test_one_session(sid: SessionId):
    websocket = cast(WebSocket, FakeWebSocket({PARAM_NAME: sid}, Address("local", 456)))

    manager = SessionManager(PARAM_NAME)
    with manager.session_for(websocket) as got_sid:
        assert got_sid == sid


def test_two_sessions_ok():
    sid1 = SessionId("123")
    sid2 = SessionId("456")
    websocket1 = cast(
        WebSocket, FakeWebSocket({PARAM_NAME: sid1}, Address("local", 1011))
    )
    websocket2 = cast(
        WebSocket, FakeWebSocket({PARAM_NAME: sid2}, Address("local", 2022))
    )

    manager = SessionManager(PARAM_NAME)
    with manager.session_for(websocket1) as got_sid1:
        assert got_sid1 == sid1
        with manager.session_for(websocket2) as got_sid2:
            assert got_sid2 == sid2


def test_reuse_after_disconnect():
    sid = SessionId("654")
    websocket = cast(WebSocket, FakeWebSocket({PARAM_NAME: sid}, Address("local", 987)))

    manager = SessionManager(PARAM_NAME)
    # We use try/except because pyright doesn't know pytest.raises() swallows exceptions
    try:
        with manager.session_for(websocket) as got_sid:
            assert got_sid == sid
            raise WebSocketDisconnect()
    except WebSocketDisconnect:
        pass
    else:
        # This shouldn't be reached
        assert False

    with manager.session_for(websocket) as got_sid:
        assert got_sid == sid


@pytest.mark.parametrize(
    "sid,client1,client2",
    [
        # Duplicate from different clients
        (
            SessionId("123"),
            Address("local", 1011),
            Address("local", 2022),
        ),
        # Duplicate from the same client
        (
            SessionId("abc"),
            Address("local", 1011),
            Address("local", 1011),
        ),
    ],
)
def test_two_sessions_conflict(sid: SessionId, client1: Address, client2: Address):
    websocket1 = cast(WebSocket, FakeWebSocket({PARAM_NAME: sid}, client1))
    websocket2 = cast(WebSocket, FakeWebSocket({PARAM_NAME: sid}, client2))

    manager = SessionManager(PARAM_NAME)
    with pytest.raises(SessionException):
        with manager.session_for(websocket1) as got_sid1:
            assert got_sid1 == sid
            with manager.session_for(websocket2):
                pass
