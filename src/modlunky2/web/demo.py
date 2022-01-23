from serde import serde
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from modlunky2.web.api.framework.multiplexing import (
    SendConnection,
    WSMultiplexer,
    WSMultiplexerRoute,
)


async def hello_world(_request: Request):
    return PlainTextResponse("Hello world!")


@serde
class EchoMessage:
    message: str


async def echo(connection: SendConnection, msg: EchoMessage):
    await connection.send(msg)


multiplexer = WSMultiplexer([WSMultiplexerRoute(EchoMessage, echo)])
