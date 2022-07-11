from dataclasses import dataclass, field
import pytest
from starlette.datastructures import Address
from starlette.websockets import WebSocket, WebSocketDisconnect
from typing import Dict, cast

from modlunky2.web.api.framework.session import (
    _extract_hostname,
    _validate_origin,
    SessionException,
    SessionId,
    SessionManager,
)


@dataclass
class FakeWebSocket:
    path_params: Dict[str, str]
    client: Address
    headers: Dict[str, str] = field(default_factory=dict)


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


def test_session_with_origin_accepted():
    websocket = cast(
        WebSocket,
        FakeWebSocket(
            {PARAM_NAME: SessionId("2001")},
            Address("local", 456),
            {"origin": "http://[::1]:9526"},
        ),
    )

    manager = SessionManager(PARAM_NAME)
    with manager.session_for(websocket) as got_sid:
        assert got_sid == "2001"


def test_session_with_origin_rejected():
    websocket = cast(
        WebSocket,
        FakeWebSocket(
            {PARAM_NAME: SessionId("2002")},
            Address("local", 456),
            {"origin": "null"},
        ),
    )

    manager = SessionManager(PARAM_NAME)
    with pytest.raises(SessionException):
        with manager.session_for(websocket):
            pass


@pytest.mark.parametrize(
    "origin", ["http://localhost", "https://localhost:3000", "http://127.0.0.1:3000"]
)
def test_validate_origin_accepted(origin):
    # Just checking that no exception is thrown
    _validate_origin(origin)


@pytest.mark.parametrize("origin", ["null", "foo", "http://example.com"])
def test_validate_origin_rejected(origin):
    with pytest.raises(SessionException):
        _validate_origin(origin)


@pytest.mark.parametrize(
    "netloc,expected",
    [
        ("example1.com", "example1.com"),
        ("example2.com:443", "example2.com"),
        ("localhost", "localhost"),
        ("localhost:3000", "localhost"),
        ("1.2.3.4", "1.2.3.4"),
        ("5.6.7.8:99", "5.6.7.8"),
        ("[::1]", "[::1]"),
        ("[::1]:80", "[::1]"),
    ],
)
def test_extract_hostname(netloc, expected):
    actual = _extract_hostname(netloc)
    assert actual == expected
