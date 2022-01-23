import threading
import typing
from typing import Callable

import anyio
from hypercorn.asyncio import serve
from hypercorn.config import Config as HypercornConfig
from hypercorn.typing import ASGI3Framework
from starlette.applications import Starlette
from starlette.routing import Mount, Route

import modlunky2.web.demo as demo


def launch_in_thread() -> Callable[[], None]:
    shutting_down = threading.Event()
    thread = threading.Thread(target=_async_worker, args=(shutting_down,))
    thread.start()

    def callback():
        shutting_down.set()
        thread.join()

    return callback


def _async_worker(shutting_down: threading.Event):
    routes = [
        Route("/", demo.hello_world),
        Mount("/echo", routes=[demo.multiplexer.starlette_route]),
    ]
    app = Starlette(debug=True, routes=routes)

    hypercorn_conf = HypercornConfig()
    hypercorn_conf.bind = "127.0.0.1:9526"
    hypercorn_conf.websocket_ping_interval = 30.0

    async def shutdown_trigger():
        await anyio.to_thread.run_sync(shutting_down.wait)

    async def _serve():
        await serve(
            # Hypercorn's ASGI3Framework uses a more precise type than Starlette
            typing.cast(ASGI3Framework, app),
            hypercorn_conf,
            shutdown_trigger=shutdown_trigger,
        )

    anyio.run(_serve)
