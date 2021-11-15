import asyncio
import json
import logging
import random
import threading

from urllib.parse import urljoin

import websockets

# These are needed to make IDE and pyinstaller happy because
# the websockets library uses a weird lazy loader
import websockets.exceptions
from websockets.legacy.client import connect as ws_connect

from modlunky2.config import Config
from modlunky2.utils import tb_info


logger = logging.getLogger("modlunky2")


class WebSocketThread(threading.Thread):
    def __init__(self, modlunky_config: Config, task_manager):
        super().__init__(daemon=True)
        self.modlunky_config = modlunky_config
        self.task_manager = task_manager
        self.api_token = modlunky_config.config_file.spelunky_fyi_api_token
        self.backoff = 0.8
        self.max_backoff = 5
        self.retry_num = 0
        self.websocket = None

        self.task_manager.register_handler(
            "fyi:install-complete", self.install_complete_sync, True
        )

    def install_complete_sync(self, channel_name):
        return asyncio.get_event_loop().run_until_complete(
            self.install_complete(channel_name)
        )

    async def install_complete(self, channel_name):
        return await self.send(
            {
                "action": "install-complete",
                "channel-name": channel_name,
            }
        )

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

    async def send(self, payload):
        if self.websocket is None:
            logger.warning("Send message on disconnected websocket.")
            return

        return await self.websocket.send(json.dumps(payload))

    async def handle_message(self, message):
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

        if payload["action"] in ["web-connected", "hello"]:
            if "channel-name" not in payload:
                return

            await self.send(
                {
                    "action": "announce",
                    "channel-name": payload["channel-name"],
                }
            )

        elif payload["action"] == "web-disconnected":
            pass
        elif payload["action"] == "install":
            await self.handle_install(payload["channel-name"], payload.get("data", {}))
        else:
            logger.debug("Unknown action (%s). Ignoring", payload)

    async def handle_install(self, channel_name, data):

        if "install-code" not in data:
            logger.warning("Invalid install request: %s", data)
            return

        kwargs = {
            "install_dir": self.modlunky_config.install_dir,
            "spelunky_fyi_root": self.modlunky_config.config_file.spelunky_fyi_root,
            "api_token": self.api_token,
            "install_code": data["install-code"],
            "mod_file_id": data.get("mod-file-id"),
            "channel_name": channel_name,
            "overwrite": False,
        }
        self.task_manager.call("install:install_fyi_mod", **kwargs)

    async def listen_inner(self):
        headers = {"Authorization": f"Token {self.api_token}"}
        try:
            self.websocket = await ws_connect(self.ws_url, extra_headers=headers)
            self.retry_num = 0
            logger.info("Connected to spelunky.fyi")
            async for message in self.websocket:
                logger.debug(message)
                await self.handle_message(message)
        finally:
            if self.websocket is not None:
                try:
                    await self.websocket.close()
                except Exception:  # pylint: disable=broad-except
                    pass
            self.websocket = None

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
                    "Websocket connection went away. Will keep trying...",
                )
                await asyncio.sleep(backoff)
            except ConnectionError:
                backoff = self.get_backoff()
                logger.debug(
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

        await asyncio.sleep(1)

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
