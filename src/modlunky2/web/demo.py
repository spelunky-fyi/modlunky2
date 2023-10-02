import logging
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import PlainTextResponse

logger = logging.getLogger(__name__)


async def hello_world(_request: Request):
    return PlainTextResponse("Hello world!")


def make_asgi_app() -> Starlette:
    routes = [
        Route("/", hello_world),
    ]
    return Starlette(debug=True, routes=routes)
