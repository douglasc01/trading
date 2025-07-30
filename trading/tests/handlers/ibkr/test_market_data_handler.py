from collections import deque
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from ibapi.client import EClient
from ibapi.common import BarData, TickAttribBidAsk, TickAttribLast
from ibapi.contract import ContractDetails

from trading.handlers.ibkr.market_data_handler import MarketDataHandler, MarketDataRequestManager
from trading.types.ibkr.market_data import Bar, BidAskTick, MidpointTick, ScannerData, TickType, TradeTick
from trading.types.ibkr.requests import HistoricalDataRequest, RealtimeBarRequest, ScannerRequest, TickByTickDataRequest


class TestMarketDataRequestManager:
    def test_init(self) -> None:
        manager = MarketDataRequestManager()
        assert isinstance(manager.response, deque)
        assert manager.response.maxlen == 10
        assert hasattr(manager, "lock")

    def test_init_custom_window(self) -> None:
        manager = MarketDataRequestManager(window_length=5)
        assert manager.response.maxlen == 5


class TestMarketDataHandler:
    @pytest.fixture
    def mock_client(self) -> Mock:
        return Mock(spec=EClient)

    @pytest.fixture
    def market_data_handler(self, mock_client: Mock) -> MarketDataHandler:
        return MarketDataHandler(mock_client)

    @pytest.fixture
    def mock_contract(self) -> Mock:
        contract = Mock()
        contract.symbol = "AAPL"
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        return contract

    @pytest.fixture
    def sample_bar_data(self) -> Mock:
        bar_data = Mock(spec=BarData)
        bar_data.date = "20231201 09:30:00 UTC"
        bar_data.open = 150.0
        bar_data.high = 151.0
        bar_data.low = 149.5
        bar_data.close = 150.5
        bar_data.volume = 1000
        bar_data.wap = 150.25
        bar_data.barCount = 10
        return bar_data

    def test_init(self, mock_client: Mock) -> None:
        handler = MarketDataHandler(mock_client)
        assert handler.client == mock_client
        assert hasattr(handler, "_responses")
        assert hasattr(handler, "_window_length")
        assert hasattr(handler, "_realtime_responses")
        assert handler._window_length == 10

    def test_init_custom_window(self, mock_client: Mock) -> None:
        handler = MarketDataHandler(mock_client, window_length=5)
        assert handler._window_length == 5

    def test_request_tick_by_tick_data(
        self, market_data_handler: MarketDataHandler, mock_client: Mock, mock_contract: Mock
    ) -> None:
        request = TickByTickDataRequest(
            request_id=123,
            contract=mock_contract,
            tick_type=TickType.LAST,
            number_of_ticks=100,
            ignore_change_in_size=False,
        )

        market_data_handler.request_tick_by_tick_data(request)

        mock_client.reqTickByTickData.assert_called_once_with(
            reqId=request.request_id,
            contract=request.contract,
            tickType=request.tick_type,
            numberOfTicks=request.number_of_ticks,
            ignore_change_in_size=request.ignore_change_in_size,
        )

    def test_fetch_realtime_response_empty(self, market_data_handler: MarketDataHandler) -> None:
        result = market_data_handler.fetch_realtime_response(123)
        assert result == []

    def test_fetch_realtime_response_with_data(self, market_data_handler: MarketDataHandler) -> None:
        request_id = 123
        test_data = ["data1", "data2", "data3"]

        with market_data_handler._realtime_responses[request_id].lock:
            market_data_handler._realtime_responses[request_id].response.extend(test_data)

        result = market_data_handler.fetch_realtime_response(request_id)
        assert result == test_data

    def test_cancel_tick_by_tick_data(self, market_data_handler: MarketDataHandler, mock_client: Mock) -> None:
        request_id = 123

        market_data_handler.cancel_tick_by_tick_data(request_id)

        mock_client.cancelTickByTickData.assert_called_once_with(request_id)

    def test_request_realtime_bars(
        self, market_data_handler: MarketDataHandler, mock_client: Mock, mock_contract: Mock
    ) -> None:
        from trading.types.ibkr.requests import BarType

        request = RealtimeBarRequest(
            request_id=123, contract=mock_contract, bar_size=5, bar_type=BarType.TRADES, extended_hours=False
        )

        market_data_handler.request_realtime_bars(request)

        mock_client.reqRealTimeBars.assert_called_once_with(
            reqId=request.request_id,
            contract=request.contract,
            barSize=request.bar_size,
            whatToShow=request.bar_type.value,
            useRTH=not request.extended_hours,
            realTimeBarsOptions=[],
        )

    def test_cancel_realtime_bars(self, market_data_handler: MarketDataHandler, mock_client: Mock) -> None:
        request_id = 123

        market_data_handler.cancel_realtime_bars(request_id)

        mock_client.cancelRealTimeBars.assert_called_once_with(request_id)

    def test_request_historical_data_keep_up_to_date(
        self, market_data_handler: MarketDataHandler, mock_client: Mock, mock_contract: Mock
    ) -> None:
        from trading.types.ibkr.requests import BarType, DateFormat

        request = HistoricalDataRequest(
            request_id=123,
            contract=mock_contract,
            end_datetime=datetime.now(),
            time_period="1 D",
            bar_size="1 min",
            bar_type=BarType.TRADES,
            extended_hours=False,
            date_format=DateFormat.FULL_DATE_TIME,
            keep_up_to_date=True,
        )

        with patch.object(market_data_handler, "_initialize_keep_up_to_date_bars"):
            result = market_data_handler.request_historical_data(request)

        mock_client.reqHistoricalData.assert_called_once()
        assert result is None

    def test_request_historical_data_not_keep_up_to_date(
        self, market_data_handler: MarketDataHandler, mock_client: Mock, mock_contract: Mock
    ) -> None:
        from trading.types.ibkr.requests import BarType, DateFormat

        request = HistoricalDataRequest(
            request_id=123,
            contract=mock_contract,
            end_datetime=datetime.now(),
            time_period="1 D",
            bar_size="1 min",
            bar_type=BarType.TRADES,
            extended_hours=False,
            date_format=DateFormat.FULL_DATE_TIME,
            keep_up_to_date=False,
        )

        with patch.object(market_data_handler, "_initialize_chain_response"):
            with patch.object(market_data_handler, "_wait_for_response", return_value=[]):
                with patch.object(market_data_handler, "_delete_response"):
                    result = market_data_handler.request_historical_data(request)

        mock_client.reqHistoricalData.assert_called_once()
        assert result == []

    def test_cancel_historical_data(self, market_data_handler: MarketDataHandler, mock_client: Mock) -> None:
        request_id = 123

        market_data_handler.cancel_historical_data(request_id)

        mock_client.cancelHistoricalData.assert_called_once_with(request_id)

    def test_fetch_historical_data(self, market_data_handler: MarketDataHandler) -> None:
        request_id = 123
        test_bars = [
            Bar(
                time=1701234567,
                open_=150.0,
                high=151.0,
                low=149.5,
                close=150.5,
                volume=1000,
                weighted_average_price=150.25,
                count=10,
            )
        ]

        with market_data_handler._lock:
            market_data_handler._responses[request_id].response = test_bars

        result = market_data_handler.fetch_historical_data(request_id)
        assert result == test_bars

    def test_request_scanner_parameters(self, market_data_handler: MarketDataHandler, mock_client: Mock) -> None:
        market_data_handler.request_scanner_parameters()
        mock_client.reqScannerParameters.assert_called_once()

    def test_request_scanner(self, market_data_handler: MarketDataHandler, mock_client: Mock) -> None:
        from ibapi.scanner import ScannerSubscription

        subscription = ScannerSubscription()
        subscription.instrument = "STK"
        subscription.locationCode = "STK.US.MAJOR"
        subscription.scanCode = "TOP_PERC_GAINERS"

        request = ScannerRequest(request_id=123, subscription=subscription)

        with patch.object(market_data_handler, "_initialize_chain_response"):
            market_data_handler.request_scanner(request)

        mock_client.reqScannerSubscription.assert_called_once()

    def test_cancel_scanner(self, market_data_handler: MarketDataHandler, mock_client: Mock) -> None:
        request_id = 123

        market_data_handler.cancel_scanner(request_id)

        mock_client.cancelScannerSubscription.assert_called_once_with(request_id)

    def test_fetch_scanner_data(self, market_data_handler: MarketDataHandler) -> None:
        request_id = 123
        test_data = [ScannerData(rank=1, contract_details=Mock(), legs_str="")]

        with market_data_handler._lock:
            market_data_handler._realtime_responses[request_id].response.append(test_data)

        result = market_data_handler.fetch_scanner_data(request_id)
        assert result == test_data

    def test_initialize_realtime_response(self, market_data_handler: MarketDataHandler) -> None:
        key = 123
        window_length = 5

        market_data_handler._initialize_realtime_response(key, window_length)

        assert key in market_data_handler._realtime_responses
        assert market_data_handler._realtime_responses[key].response.maxlen == window_length

    def test_store_realtime_response(self, market_data_handler: MarketDataHandler) -> None:
        key = 123
        response_data = "test_data"

        market_data_handler._initialize_realtime_response(key)

        market_data_handler._store_realtime_response(key, response_data)

        with market_data_handler._realtime_responses[key].lock:
            assert response_data in market_data_handler._realtime_responses[key].response

    def test_on_tick_by_tick_all_last(self, market_data_handler: MarketDataHandler) -> None:
        request_id = 123
        tick_type = 1
        time = 1701234567
        price = 150.25
        size = Decimal("100")
        last_tick_attribute = Mock(spec=TickAttribLast)
        last_tick_attribute.pastLimit = False
        last_tick_attribute.unreported = False
        exchange = "SMART"
        special_conditions = ""

        market_data_handler._initialize_realtime_response(request_id)

        market_data_handler._on_tick_by_tick_all_last(
            request_id, tick_type, time, price, size, last_tick_attribute, exchange, special_conditions
        )

        with market_data_handler._realtime_responses[request_id].lock:
            stored_data = list(market_data_handler._realtime_responses[request_id].response)
            assert len(stored_data) == 1
            assert isinstance(stored_data[0], TradeTick)

    def test_on_tick_by_tick_bid_ask(self, market_data_handler: MarketDataHandler) -> None:
        request_id = 123
        time = 1701234567
        bid_price = 150.20
        ask_price = 150.30
        bid_size = Decimal("50")
        ask_size = Decimal("75")
        bid_ask_tick_attribute = Mock(spec=TickAttribBidAsk)
        bid_ask_tick_attribute.bidPastLow = False
        bid_ask_tick_attribute.askPastHigh = False

        market_data_handler._initialize_realtime_response(request_id)

        market_data_handler._on_tick_by_tick_bid_ask(
            request_id, time, bid_price, ask_price, bid_size, ask_size, bid_ask_tick_attribute
        )

        with market_data_handler._realtime_responses[request_id].lock:
            stored_data = list(market_data_handler._realtime_responses[request_id].response)
            assert len(stored_data) == 1
            assert isinstance(stored_data[0], BidAskTick)

    def test_on_tick_by_tick_midpoint(self, market_data_handler: MarketDataHandler) -> None:
        request_id = 123
        time = 1701234567
        midpoint = 150.25

        market_data_handler._initialize_realtime_response(request_id)

        market_data_handler._on_tick_by_tick_midpoint(request_id, time, midpoint)

        with market_data_handler._realtime_responses[request_id].lock:
            stored_data = list(market_data_handler._realtime_responses[request_id].response)
            assert len(stored_data) == 1
            assert isinstance(stored_data[0], MidpointTick)

    def test_on_realtime_bar(self, market_data_handler: MarketDataHandler) -> None:
        request_id = 123
        time = 1701234567
        open_ = 150.0
        high = 151.0
        low = 149.5
        close = 150.5
        volume = Decimal("1000")
        weighted_average_price = Decimal("150.25")
        count = 10

        market_data_handler._initialize_realtime_response(request_id)

        market_data_handler._on_realtime_bar(
            request_id, time, open_, high, low, close, volume, weighted_average_price, count
        )

        with market_data_handler._realtime_responses[request_id].lock:
            stored_data = list(market_data_handler._realtime_responses[request_id].response)
            assert len(stored_data) == 1
            assert isinstance(stored_data[0], Bar)

    def test_initialize_keep_up_to_date_bars(self, market_data_handler: MarketDataHandler) -> None:
        key = 123
        window_length = 5

        market_data_handler._initialize_keep_up_to_date_bars(key, window_length)

        assert key in market_data_handler._responses
        assert market_data_handler._responses[key].response.maxlen == window_length

    def test_store_keep_up_to_date_bar(self, market_data_handler: MarketDataHandler) -> None:
        key = 123
        bar = Bar(
            time=1701234567,
            open_=150.0,
            high=151.0,
            low=149.5,
            close=150.5,
            volume=1000,
            weighted_average_price=150.25,
            count=10,
        )

        market_data_handler._initialize_keep_up_to_date_bars(key)

        market_data_handler._store_keep_up_to_date_bar(key, bar)

        with market_data_handler._responses[key].lock:
            stored_data = list(market_data_handler._responses[key].response)
            assert len(stored_data) == 1
            assert stored_data[0] == bar

    def test_on_historical_data(self, market_data_handler: MarketDataHandler, sample_bar_data: Mock) -> None:
        request_id = 123

        market_data_handler._initialize_chain_response(request_id)

        market_data_handler._on_historical_data(request_id, sample_bar_data)

        with market_data_handler._lock:
            stored_data = market_data_handler._responses[request_id].response
            assert len(stored_data) == 1
            assert isinstance(stored_data[0], Bar)

    def test_on_historical_data_update(self, market_data_handler: MarketDataHandler, sample_bar_data: Mock) -> None:
        request_id = 123

        market_data_handler._initialize_keep_up_to_date_bars(request_id)

        market_data_handler._on_historical_data_update(request_id, sample_bar_data)

        with market_data_handler._responses[request_id].lock:
            stored_data = list(market_data_handler._responses[request_id].response)
            assert len(stored_data) == 1
            assert isinstance(stored_data[0], Bar)

    def test_on_historical_data_end(self, market_data_handler: MarketDataHandler) -> None:
        request_id = 123
        start = "20231201 09:30:00"
        end = "20231201 16:00:00"

        market_data_handler._initialize_chain_response(request_id)

        market_data_handler._on_historical_data_end(request_id, start, end)

        assert market_data_handler._events[request_id].is_set()

    def test_on_scanner_data(self, market_data_handler: MarketDataHandler) -> None:
        request_id = 123
        rank = 1
        contract_details = Mock(spec=ContractDetails)
        distance = "0"
        benchmark = ""
        projection = ""
        legs_str = ""

        market_data_handler._initialize_realtime_response(request_id)

        market_data_handler._on_scanner_data(
            request_id, rank, contract_details, distance, benchmark, projection, legs_str
        )

        with market_data_handler._realtime_responses[request_id].lock:
            stored_data = list(market_data_handler._realtime_responses[request_id].response)
            assert len(stored_data) == 1
            assert isinstance(stored_data[0], ScannerData)

    def test_window_length_limits_data(self, market_data_handler: MarketDataHandler) -> None:
        request_id = 123
        window_length = 3

        market_data_handler._initialize_realtime_response(request_id, window_length)

        for i in range(5):
            market_data_handler._store_realtime_response(request_id, f"data_{i}")

        with market_data_handler._realtime_responses[request_id].lock:
            stored_data = list(market_data_handler._realtime_responses[request_id].response)
            assert len(stored_data) == window_length
            assert stored_data == ["data_2", "data_3", "data_4"]
