from starlette.requests import Request
from starlette.responses import PlainTextResponse


async def hello_world(_request: Request):
    return PlainTextResponse("Hello world!")
