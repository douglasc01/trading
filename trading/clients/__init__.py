import threading
from abc import ABC, abstractmethod


class Client(ABC):
    @abstractmethod
    def strategy_loop(self, stop_event: threading.Event) -> None:
        pass

    @abstractmethod
    def start(self) -> None:
        pass
