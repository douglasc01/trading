import threading
from concurrent import futures
from dataclasses import dataclass

from ibapi.client import EClient
from ibapi.wrapper import EWrapper

from trading import logging
from trading.handlers.ibkr.account_handler import AccountHandler
from trading.handlers.ibkr.base_handler import BaseHandler
from trading.handlers.ibkr.market_data_handler import MarketDataHandler
from trading.handlers.ibkr.order_handler import OrderHandler
from trading.utils.common import camel_to_snake

LOGGER = logging.getLogger("ibkr-client")


@dataclass
class TWSConnectionConfig:
    host: str
    port: int
    client_id: int


class IBKRClient(EWrapper, EClient):
    def __init__(
        self,
        connection_config: TWSConnectionConfig,
        base_handler: type[BaseHandler] = BaseHandler,
        data_handler: type[MarketDataHandler] = MarketDataHandler,
        order_handler: type[OrderHandler] = OrderHandler,
        account_handler: type[AccountHandler] = AccountHandler,
    ) -> None:
        EWrapper.__init__(self)
        EClient.__init__(self, wrapper=self)

        self.connection_config = connection_config
        self.base_handler = base_handler(client=self)
        self.data_handler = data_handler(client=self)
        self.order_handler = order_handler(client=self)
        self.account_handler = account_handler(client=self)
        self._initialize_callbacks()

    def _initialize_callbacks(self) -> None:
        for attr_name, attr_value in EWrapper.__dict__.items():
            if not attr_name.startswith("__") and callable(attr_value):
                handler_callback_function = f"_on_{camel_to_snake(attr_name)}"
                for handler in [
                    self.base_handler,
                    self.data_handler,
                    self.order_handler,
                    self.account_handler,
                ]:
                    if hasattr(handler, handler_callback_function):
                        setattr(self, attr_name, getattr(handler, handler_callback_function))

    def strategy_loop(self, stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            raise NotImplementedError

    def start(self) -> None:
        with futures.ThreadPoolExecutor(max_workers=2) as executor:
            try:
                self.connect(
                    self.connection_config.host,
                    self.connection_config.port,
                    self.connection_config.client_id,
                )
                stop_event = threading.Event()

                future_to_worker = {
                    executor.submit(self.run): "ibkr_client",
                    executor.submit(self.strategy_loop, stop_event): "strategy_loop",
                }

                for future in futures.as_completed(future_to_worker):
                    data = future.result()
                    LOGGER.info(f"Result from {future_to_worker[future]}: {data}")
            except KeyboardInterrupt:
                LOGGER.info("Disconnecting due to KeyboardInterrupt")
                stop_event.set()
                self.disconnect()
                raise KeyboardInterrupt
            except Exception as e:
                stop_event.set()
                self.disconnect()
                raise e
