import threading
import typing
from typing import Callable

from anyio import run
from anyio.to_thread import run_sync
from hypercorn.asyncio import serve
from hypercorn.config import Config as HypercornConfig
from hypercorn.typing import Framework

from modlunky2.config import Config
from modlunky2.web.demo import make_asgi_app


def launch_in_thread(config: Config) -> Callable[[], None]:
    shutting_down = threading.Event()
    thread = threading.Thread(target=_async_worker, args=(config, shutting_down))
    thread.start()

    def callback():
        shutting_down.set()
        thread.join()

    return callback


def _async_worker(config: Config, shutting_down: threading.Event):
    app = make_asgi_app()
    hypercorn_conf = HypercornConfig()
    hypercorn_conf.bind = f"localhost:{config.api_port}"
    hypercorn_conf.websocket_ping_interval = 30.0

    async def shutdown_trigger():
        await run_sync(shutting_down.wait)

    async def _serve():
        await serve(
            # Hypercorn's Framework uses a more precise type than Starlette
            typing.cast(Framework, app),
            hypercorn_conf,
            shutdown_trigger=shutdown_trigger,
        )

    run(_serve)
