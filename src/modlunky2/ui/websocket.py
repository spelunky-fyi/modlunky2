import asyncio
import json
import logging
import random
import threading

from urllib.parse import urljoin

import websockets

from modlunky2.utils import tb_info


logger = logging.getLogger("modlunky2")


class WebSocketThread(threading.Thread):
    def __init__(self, modlunky_config):
        super().__init__(daemon=True)
        self.modlunky_config = modlunky_config
        self.api_token = modlunky_config.config_file.spelunky_fyi_api_token
        self.backoff = 0.2
        self.max_backoff = 5
        self.retry_num = 0

    def token_changed(self):
        return self.modlunky_config.config_file.spelunky_fyi_api_token != self.api_token

    def get_backoff(self):
        backoff = self.backoff * 2 ** self.retry_num + random.uniform(0, 1)
        self.retry_num += 1
        return min(backoff, self.max_backoff)

    @property
    def ws_url(self):
        return urljoin(
            self.modlunky_config.config_file.spelunky_fyi_ws_root,
            "ws/gateway/ml/",
        )

    async def handle_message(self, websocket, message):
        try:
            payload = json.loads(message)
        except Exception:  # pylint: disable=broad-except
            logger.debug(
                "Received unexpected message (%s) from spelunky.fyi. Ignoring...",
                message,
            )

        if "action" not in payload:
            logger.debug(
                "Received unexpected message (%s) from spelunky.fyi. Ignoring...",
                message,
            )

        if payload["action"] == "web-connected":
            if "channel-name" not in payload:
                return

            await websocket.send(
                json.dumps(
                    {
                        "action": "announce",
                        "channel-name": payload["channel-name"],
                    }
                )
            )
        elif payload["action"] == "web-disconnected":
            pass
        elif payload["action"] == "install":
            pass
        else:
            logger.debug("Unknown action (%s). Ignoring", payload)

    async def listen_inner(self):
        headers = {"Authorization": f"Token {self.api_token}"}
        async with websockets.connect(self.ws_url, extra_headers=headers) as websocket:
            self.retry_num = 0
            logger.info("Connected to spelunky.fyi")
            async for message in websocket:
                logger.info(message)
                await self.handle_message(websocket, message)

    async def listen(self):
        while True:
            try:
                await self.listen_inner()
                break
            except websockets.exceptions.InvalidStatusCode:
                logger.warning("Invalid Request, Do you have an invalid auth token?")
                await asyncio.sleep(300)
            except websockets.exceptions.ConnectionClosedError:
                backoff = self.get_backoff()
                logger.warning(
                    "Websocket connection went away. Trying again in %s seconds",
                    backoff,
                )
                await asyncio.sleep(backoff)
            except ConnectionError:
                backoff = self.get_backoff()
                logger.warning(
                    "Couldn't get connection to spelunky.fyi. Trying again in %s seconds...",
                    backoff,
                )
                await asyncio.sleep(backoff)
            except Exception:  # pylint: disable=broad-except
                backoff = self.get_backoff()
                logger.critical("Unexpected failure: %s", tb_info())
                await asyncio.sleep(backoff)

    async def healthcheck(self):
        while True:
            await asyncio.sleep(1)
            if self.token_changed():
                logger.debug("Token Changed. Exiting...")
                return

    async def run_async(self):

        tasks = []

        logger.debug("starting healthcheck")
        tasks.append(asyncio.create_task(self.healthcheck()))

        logger.debug("starting listener")
        tasks.append(asyncio.create_task(self.listen()))

        _, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        for task in pending:
            task.cancel()

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        if self.api_token is None:
            logger.warning("Started websocket thread with no token. Exiting...")
            return

        try:
            asyncio.get_event_loop().run_until_complete(self.run_async())
        except Exception:  # pylint: disable=broad-except
            logger.critical("Failed running websocket loop: %s", tb_info())
