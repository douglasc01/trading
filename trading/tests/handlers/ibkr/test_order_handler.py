from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.order import Order

from trading.handlers.ibkr.order_handler import OrderHandler
from trading.types.ibkr.requests import OrderRequest


class TestOrderHandler:
    @pytest.fixture
    def mock_client(self) -> Mock:
        return Mock(spec=EClient)

    @pytest.fixture
    def order_handler(self, mock_client: Mock) -> OrderHandler:
        return OrderHandler(mock_client)

    @pytest.fixture
    def mock_contract(self) -> Mock:
        contract = Mock(spec=Contract)
        contract.symbol = "AAPL"
        contract.secType = "STK"
        return contract

    @pytest.fixture
    def mock_order(self) -> Mock:
        order = Mock(spec=Order)
        order.action = "BUY"
        order.totalQuantity = 100
        order.orderType = "LMT"
        return order

    @pytest.fixture
    def order_request(self, mock_contract: Mock, mock_order: Mock) -> OrderRequest:
        return OrderRequest(request_id=123, contract=mock_contract, order=mock_order)

    def test_init(self, mock_client: Mock) -> None:
        handler = OrderHandler(mock_client)
        assert handler.client == mock_client
        assert hasattr(handler, "_lock")
        assert hasattr(handler, "_responses")
        assert hasattr(handler, "_events")

    def test_place_order(
        self,
        order_handler: OrderHandler,
        mock_client: Mock,
        order_request: OrderRequest,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        with caplog.at_level("INFO"):
            order_handler.place_order(order_request)

        mock_client.placeOrder.assert_called_once_with(
            order_request.request_id, order_request.contract, order_request.order
        )
        assert "Placing order" in caplog.text

    def test_place_buy_order(self, order_handler: OrderHandler, mock_client: Mock) -> None:
        request_id = 456
        symbol = "AAPL"
        quantity = 50
        limit_price = 150.0

        with patch("trading.handlers.ibkr.order_handler.create_stock_contract") as mock_create_contract:
            with patch("trading.handlers.ibkr.order_handler.create_simple_order") as mock_create_order:
                mock_contract = Mock(spec=Contract)
                mock_contract.symbol = symbol
                mock_contract.secType = "STK"
                mock_order = Mock(spec=Order)
                mock_order.action = "BUY"
                mock_order.totalQuantity = quantity
                mock_order.orderType = "LMT"
                mock_order.lmtPrice = limit_price
                mock_create_contract.return_value = mock_contract
                mock_create_order.return_value = mock_order

                order_handler.place_buy_order(request_id, symbol, quantity, limit_price)

                mock_create_contract.assert_called_once_with(symbol)
                mock_create_order.assert_called_once_with(
                    action="BUY", quantity=quantity, limit_price=limit_price, extended_hours=False
                )
                mock_client.placeOrder.assert_called_once_with(request_id, mock_contract, mock_order)

    def test_place_buy_order_no_limit(self, order_handler: OrderHandler, mock_client: Mock) -> None:
        request_id = 456
        symbol = "AAPL"
        quantity = 50

        with patch("trading.handlers.ibkr.order_handler.create_stock_contract") as mock_create_contract:
            with patch("trading.handlers.ibkr.order_handler.create_simple_order") as mock_create_order:
                mock_contract = Mock(spec=Contract)
                mock_contract.symbol = symbol
                mock_contract.secType = "STK"
                mock_order = Mock(spec=Order)
                mock_order.action = "BUY"
                mock_order.totalQuantity = quantity
                mock_order.orderType = "MKT"
                mock_create_contract.return_value = mock_contract
                mock_create_order.return_value = mock_order

                order_handler.place_buy_order(request_id, symbol, quantity)

                mock_create_order.assert_called_once_with(
                    action="BUY", quantity=quantity, limit_price=None, extended_hours=False
                )

    def test_cancel_order(
        self, order_handler: OrderHandler, mock_client: Mock, caplog: pytest.LogCaptureFixture
    ) -> None:
        request_id = 123

        with caplog.at_level("INFO"):
            order_handler.cancel_order(request_id)

        mock_client.cancelOrder.assert_called_once_with(request_id)
        assert f"Cancelling order: {request_id}" in caplog.text

    def test_request_global_cancel(
        self, order_handler: OrderHandler, mock_client: Mock, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level("INFO"):
            order_handler.request_global_cancel()

        mock_client.reqGlobalCancel.assert_called_once()
        assert "Requesting global cancel" in caplog.text

    def test_fetch_order_status_not_found(self, order_handler: OrderHandler) -> None:
        result = order_handler.fetch_order_status(999)
        assert result is False

    def test_fetch_order_status_found(self, order_handler: OrderHandler) -> None:
        order_id = 123
        quantity = 100

        with order_handler._lock:
            order_handler._responses[order_id].response = quantity

        result = order_handler.fetch_order_status(order_id)
        assert result is True

    def test_on_order_status(self, order_handler: OrderHandler, caplog: pytest.LogCaptureFixture) -> None:
        order_id = 123
        status = "Submitted"
        filled = Decimal("50")
        remaining = Decimal("50")
        avg_fill_price = 150.25
        perm_id = 456
        parent_id = 0
        last_fill_price = 150.25
        client_id = 123
        why_held = ""
        mkt_cap_price = 150.25

        with order_handler._lock:
            order_handler._responses[order_id].response = 100

        with caplog.at_level("INFO"):
            order_handler._on_order_status(
                order_id,
                status,
                filled,
                remaining,
                avg_fill_price,
                perm_id,
                parent_id,
                last_fill_price,
                client_id,
                why_held,
                mkt_cap_price,
            )

        assert "Received order status" in caplog.text
        assert order_id in order_handler._responses

    def test_on_order_status_completed(self, order_handler: OrderHandler, caplog: pytest.LogCaptureFixture) -> None:
        order_id = 123
        status = "Filled"
        filled = Decimal("100")
        remaining = Decimal("0")
        avg_fill_price = 150.25
        perm_id = 456
        parent_id = 0
        last_fill_price = 150.25
        client_id = 123
        why_held = ""
        mkt_cap_price = 150.25

        with order_handler._lock:
            order_handler._responses[order_id].response = 100

        with caplog.at_level("INFO"):
            order_handler._on_order_status(
                order_id,
                status,
                filled,
                remaining,
                avg_fill_price,
                perm_id,
                parent_id,
                last_fill_price,
                client_id,
                why_held,
                mkt_cap_price,
            )

        assert "Received order status" in caplog.text
        assert order_id not in order_handler._responses

    def test_place_order_stores_response(self, order_handler: OrderHandler, order_request: OrderRequest) -> None:
        order_handler.place_order(order_request)

        with order_handler._lock:
            assert order_request.request_id in order_handler._responses
            assert order_handler._responses[order_request.request_id].response == order_request.order.totalQuantity
