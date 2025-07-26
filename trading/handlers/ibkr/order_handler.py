import logging
from decimal import Decimal

from trading.handlers.ibkr import Handler
from trading.types.ibkr.requests import OrderRequest
from trading.utils.ibkr import create_simple_order, create_stock_contract

LOGGER = logging.getLogger("order-handler")


class OrderHandler(Handler):
    def place_order(self, request: OrderRequest) -> None:
        LOGGER.info(
            f"Placing order: {request.request_id}, {request.contract.symbol}-{request.contract.secType}, "
            f"action: {request.order.action}, total quantity: {request.order.totalQuantity}, "
            f"orderType: {request.order.orderType}"
        )
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#place-order"""
        self.client.placeOrder(request.request_id, request.contract, request.order)
        self._store_response(request.request_id, request.order.totalQuantity)

    def place_buy_order(
        self,
        request_id: int,
        symbol: str,
        quantity: int,
        limit_price: float | None = None,
        extended_hours: bool = False,
    ) -> None:
        """
        Places a buy order for a given stock symbol.

        Arguments:
            request_id: int
                The request ID of the order.
            symbol: str
                The symbol of the stock to buy.
            quantity: int
                The quantity of the order.
            limit_price: float | None
                The price to limit the order at.
            extended_hours: bool
                Whether the order can be executed during extended hours.
        """
        contract = create_stock_contract(symbol)
        order = create_simple_order(
            action="BUY",
            quantity=quantity,
            limit_price=limit_price,
            extended_hours=extended_hours,
        )
        self.place_order(OrderRequest(request_id=request_id, contract=contract, order=order))

    def place_sell_order(
        self,
        request_id: int,
        symbol: str,
        quantity: int,
        limit_price: float | None = None,
        extended_hours: bool = False,
    ) -> None:
        """
        Places a sell order for a given stock symbol.

        Arguments:
            request_id: int
                The request ID of the order.
            symbol: str
                The symbol of the stock to sell.
            quantity: int
                The quantity of the order.
            limit_price: float | None
                The price to limit the order at.
            extended_hours: bool
                Whether the order can be executed during extended hours.
        """
        contract = create_stock_contract(symbol)
        order = create_simple_order(
            action="SELL",
            quantity=quantity,
            limit_price=limit_price,
            extended_hours=extended_hours,
        )
        self.place_order(OrderRequest(request_id=request_id, contract=contract, order=order))

    def cancel_order(self, request_id: int) -> None:
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#cancel-order"""
        LOGGER.info(f"Cancelling order: {request_id}")
        self.client.cancelOrder(request_id)

    def request_global_cancel(self) -> None:
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#request-global-cancel"""
        LOGGER.info("Requesting global cancel")
        self.client.reqGlobalCancel()

    def _on_order_status(
        self,
        order_id: int,
        status: str,
        filled: Decimal,
        remaining: Decimal,
        avg_fill_price: float,
        perm_id: int,
        parent_id: int,
        last_fill_price: float,
        client_id: int,
        why_held: str,
        mkt_cap_price: float,
    ) -> None:
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#order-status"""
        LOGGER.info(
            f"Received order status: {order_id}, {status}, {filled}, {remaining}, {avg_fill_price}, {perm_id}, "
            f"{parent_id}, {last_fill_price}, {client_id}, {why_held}, {mkt_cap_price}"
        )
        if remaining == 0:
            self._delete_response(order_id)

    def fetch_order_status(self, order_id: int) -> bool:
        with self._lock:
            if order_id not in self._responses:
                return False
            else:
                return True
