import time
import logging
import threading
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass
from multiprocessing import Process, Queue
from queue import Empty

from modlunky2.utils import tb_info

from .logs import register_queue_handler, QueueHandler

logger = logging.getLogger(__name__)


PING_INTERVAL = 1
PING_TIMEOUT = 5


@dataclass
class Message:
    name: str
    kwargs: Optional[Dict[str, Any]] = None


@dataclass
class Task:
    callback: Callable
    threaded: bool = False
    on_complete: Optional[str] = None


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

    def register(self, name, callback, threaded=False, on_complete=None):
        if self._started:
            raise RuntimeError(
                f"Attempted to register {name!r} after worker was started..."
            )

        if name in self._receivers:
            raise RuntimeError(f"{name} is already registered...")

        self._receivers[name] = Task(callback, threaded, on_complete)

    def process_tasks(self, log_queue, log_level=logging.INFO):
        queue_handler = QueueHandler(log_queue)
        register_queue_handler(queue_handler, log_level)
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
        task = self._receivers.get(msg.name)
        if task is None:
            logger.warning(
                "Worker: Received unexpected command (%s). Ignoring...", msg.name
            )
            return

        kwargs = {}
        if msg.kwargs is not None:
            kwargs.update(msg.kwargs)

        def func():
            try:
                task.callback(self.call, **kwargs)
            except Exception:  # pylint: disable=broad-except
                logger.critical(
                    "Failed to execute command %s: %s", repr(msg.name), tb_info()
                )
            if task.on_complete:
                self.call(task.on_complete)

        if task.threaded:
            thread = threading.Thread(target=func, daemon=True)
            thread.start()
        else:
            func()

    def send_message(self, msg: Message):
        self.tx_queue.put_nowait(msg)


class TaskManager:
    def __init__(self, log_queue, log_level=logging.INFO):
        self.tx_queue = Queue()
        self.rx_queue = Queue()
        self.log_queue = log_queue
        self.log_level = log_level
        self.worker = Worker(rx_queue=self.tx_queue, tx_queue=self.rx_queue)
        self.worker_process = None
        self._receivers = {}
        self.register("pong", self.handle_pong)

    def register(self, name, callback, overwrite=False):
        if not overwrite and name in self._receivers:
            raise RuntimeError(f"{name} is already registered...")
        self._receivers[name] = callback

    def register_task(self, name, callback, threaded=False, on_complete=None):
        self.worker.register(name, callback, threaded, on_complete)

    def register_handler(self, name, callback, overwrite=False):
        self.register(name, callback, overwrite)

    def call(self, name, **kwargs):
        if not kwargs:
            kwargs = None
        msg = Message(name, kwargs)
        self.send_message(msg)

    def start_process(self):
        self.worker_process = Process(
            target=self.worker.process_tasks, args=(self.log_queue, self.log_level)
        )
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
        if msg.name != "pong":
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
