from contextlib import asynccontextmanager
from functools import partial
import logging
import time
from typing import NoReturn
from anyio import create_task_group, current_time, sleep
from dataclasses import dataclass
from serde import serde
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from modlunky2.web.api.framework.multiplexing import (
    SendConnection,
    WSMultiplexer,
    WSMultiplexerRoute,
)
from modlunky2.web.api.framework.pubsub import PubSubManager, PubSubTopic, ServiceLevel
from starlette.requests import Request
from starlette.responses import PlainTextResponse

logger = logging.getLogger(__name__)


async def hello_world(_request: Request):
    return PlainTextResponse("Hello world!")


@serde
@dataclass
class EchoMessage:
    message: str


async def echo(connection: SendConnection, msg: EchoMessage):
    await connection.send(msg)


@serde
@dataclass
class TimeTick:
    now: float


async def ticker(pub_manager: PubSubManager) -> NoReturn:
    period = 5  # in seconds
    while True:
        delay = period - current_time() % period
        civil_time = time.time()

        pub_manager.publish(TimeTick(civil_time))
        await sleep(delay)


@asynccontextmanager
async def app_lifespan(pub_manager: PubSubManager, _app: Starlette):
    async with create_task_group() as tg:
        tg.start_soon(ticker, pub_manager)
        yield
        tg.cancel_scope.cancel()


def make_asgi_app() -> Starlette:
    topics = [PubSubTopic(TimeTick, ServiceLevel.MAY_DROP)]
    pub_manager = PubSubManager(topics)
    multiplexer = WSMultiplexer(
        (WSMultiplexerRoute(EchoMessage, echo),) + pub_manager.multiplexer_routes
    )
    routes = [
        Route("/", hello_world),
        Mount("/echo", routes=[multiplexer.starlette_route]),
    ]
    return Starlette(
        debug=True, routes=routes, lifespan=partial(app_lifespan, pub_manager)
    )
