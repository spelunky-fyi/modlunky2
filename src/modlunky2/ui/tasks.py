import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from multiprocessing import Process, Queue
from queue import Empty

logger = logging.getLogger("modlunky2")


PING_INTERVAL = 1
PING_TIMEOUT = 5


@dataclass
class Message:
    name: str
    kwargs: Optional[Dict[str, Any]] = None


class Worker:
    def __init__(self, rx_queue, tx_queue):
        self.rx_queue = rx_queue
        self.tx_queue = tx_queue
        self.last_ping = None
        self._started = False
        self._receivers = {}

    def call(self, name, **kwargs):
        if not kwargs:
            kwargs = None
        msg = Message(name, kwargs)
        self.send_message(msg)

    def register(self, name, callback):
        if self._started:
            raise RuntimeError(
                f"Attempted to register {name!r} after worker was started..."
            )

        if name in self._receivers:
            raise RuntimeError(f"{name} is already registered...")

        self._receivers[name] = callback

    def process_tasks(self):
        self._started = True
        self.last_ping = time.time()
        while True:
            try:
                msg = self.rx_queue.get(block=True, timeout=1)
            except Empty:
                now = time.time()
                if now - self.last_ping > PING_TIMEOUT:
                    logger.warning("Worker: Stopped seeing pings. Shutting down...")
                    return
                continue

            if msg.name == "quit":
                logger.info("Worker: Shutting down...")
                return
            elif msg.name == "ping":
                self.last_ping = time.time()
                self.call("pong")
                continue

            self.dispatch(msg)

    def dispatch(self, msg):
        func = self._receivers.get(msg.name)
        if func is None:
            logger.warning(
                "Worker: Received unexpected command (%s). Ignoring...", msg.name
            )
            return

        kwargs = {}
        if msg.kwargs is not None:
            kwargs.update(msg.kwargs)

        try:
            func(self, **kwargs)
        except Exception as err:  # pylint: disable=broad-except
            logger.critical("Failed to execute command %s: %s", repr(msg.name), err)

    def send_message(self, msg: Message):
        self.tx_queue.put_nowait(msg)


class TaskManager:
    def __init__(self):
        self.tx_queue = Queue()
        self.rx_queue = Queue()
        self.worker = Worker(rx_queue=self.tx_queue, tx_queue=self.rx_queue)
        self.worker_process = None
        self._receivers = {}
        self.register("pong", self.handle_pong)

    def register(self, name, callback):
        if name in self._receivers:
            raise RuntimeError(f"{name} is already registered...")
        self._receivers[name] = callback

    def register_task(self, name, callback):
        self.worker.register(name, callback)

    def register_handler(self, name, callback):
        self.register(name, callback)

    def call(self, name, **kwargs):
        if not kwargs:
            kwargs = None
        msg = Message(name, kwargs)
        self.send_message(msg)

    def start_process(self):
        self.worker_process = Process(target=self.worker.process_tasks)
        self.worker_process.start()

    def is_alive(self):
        return self.worker_process.is_alive()

    def quit(self):
        self.send_message(Message("quit"))

    def ping(self):
        self.send_message(Message("ping"))

    def send_message(self, msg: Message):
        self.tx_queue.put_nowait(msg)

    def receive_message(self) -> Message:
        try:
            return self.rx_queue.get_nowait()
        except Empty:
            return None

    def handle_pong(self):
        pass

    def dispatch(self, msg):
        logger.debug("Received Message: %s", msg)

        func = self._receivers.get(msg.name)
        if func is None:
            logger.warning(
                "Received unexpected command (%s) from worker. Ignoring...", msg.name
            )
            return

        kwargs = {}
        if msg.kwargs is not None:
            kwargs.update(msg.kwargs)

        func(**kwargs)
