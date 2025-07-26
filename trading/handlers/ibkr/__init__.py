import copy
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from ibapi.client import EClient

LOGGER = logging.getLogger("handler")


@dataclass
class ResponseManager:
    response: Any | None = None
    lock: threading.Lock = threading.Lock()


class Handler:
    def __init__(self, client: EClient) -> None:
        self.client = client
        self._lock = threading.Lock()
        self._responses: defaultdict[int, ResponseManager] = defaultdict(ResponseManager)
        self._events: defaultdict[int, threading.Event] = defaultdict(threading.Event)

    def _wait_for_response(self, key: int, timeout: float = 10) -> Any:
        if not self._events[key].wait(timeout):
            raise TimeoutError(f"Timeout waiting for response for key: {key}")

        with self._responses[key].lock:
            response = self._responses[key].response
            self._events[key].clear()
            return copy.deepcopy(response)

    def _store_response(self, key: int, response: Any) -> None:
        with self._responses[key].lock:
            self._responses[key].response = response
            self._events[key].set()

    def _initialize_chain_response(self, key: int) -> None:
        with self._responses[key].lock:
            self._responses[key].response = []

    def _store_chain_response(self, key: int, response: Any) -> None:
        with self._responses[key].lock:
            self._responses[key].response.append(response)

    def _end_chain_response(self, key: int) -> None:
        with self._responses[key].lock:
            self._events[key].set()

    def _delete_response(self, key: int) -> None:
        with self._lock:
            if key not in self._responses:
                return
            response_lock = self._responses[key].lock

        with response_lock:
            with self._lock:
                if key in self._responses:
                    del self._responses[key]
