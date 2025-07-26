import logging
import os
import threading
from collections import defaultdict, deque
from datetime import datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from ibapi.client import EClient
from ibapi.common import BarData, TickAttribBidAsk, TickAttribLast
from ibapi.contract import ContractDetails

from trading.handlers.ibkr import Handler
from trading.types.ibkr.market_data import Bar, BidAskTick, MidpointTick, ScannerData, TickType, TradeTick
from trading.types.ibkr.requests import HistoricalDataRequest, RealtimeBarRequest, ScannerRequest, TickByTickDataRequest

LOGGER = logging.getLogger("market-data-handler")


class MarketDataRequestManager:
    def __init__(self, window_length: int = 10) -> None:
        self.response: deque[Any] = deque(maxlen=window_length)
        self.lock = threading.Lock()


class MarketDataHandler(Handler):
    def __init__(self, client: EClient, window_length: int = 10) -> None:
        super().__init__(client)
        self._responses: defaultdict[int, Any]
        self._window_length = window_length
        self._realtime_responses: defaultdict[int, MarketDataRequestManager] = defaultdict(MarketDataRequestManager)

    def _initialize_realtime_response(self, key: int, window_length: int = 10) -> None:
        """Initializes a new realtime response manager"""
        with self._lock:
            self._realtime_responses[key] = MarketDataRequestManager(window_length)

    def _store_realtime_response(self, key: int, response: Any) -> None:
        """Appends the response to the realtime deque"""
        with self._realtime_responses[key].lock:
            self._realtime_responses[key].response.append(response)

    def fetch_realtime_response(self, key: int) -> Any:
        """Fetches the realtime response as a snapshot of the deque"""
        with self._realtime_responses[key].lock:
            return list(self._realtime_responses[key].response)

    def request_tick_by_tick_data(
        self,
        request: TickByTickDataRequest,
    ) -> None:
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#request-tick-data"""
        self.client.reqTickByTickData(
            reqId=request.request_id,
            contract=request.contract,
            tickType=request.tick_type,
            numberOfTicks=request.number_of_ticks,
            ignore_change_in_size=request.ignore_change_in_size,
        )

    def cancel_tick_by_tick_data(self, request_id: int) -> None:
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#cancel-tick-data"""
        self.client.cancelTickByTickData(request_id)

    def _on_tick_by_tick_all_last(
        self,
        request_id: int,
        tick_type: int,
        time: int,
        price: float,
        size: Decimal,
        last_tick_attribute: TickAttribLast,
        exchange: str,
        special_conditions: str,
    ) -> None:
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#receive-tick-data"""
        tick = TradeTick(
            tick_type=TickType.LAST if tick_type == 0 else TickType.ALL_LAST,
            time=time,
            price=price,
            size=size,
            past_limit=last_tick_attribute.pastLimit,
            unreported=last_tick_attribute.unreported,
            exchange=exchange,
            special_conditions=special_conditions,
        )
        self._store_realtime_response(request_id, tick)

    def _on_tick_by_tick_bid_ask(
        self,
        request_id: int,
        time: int,
        bid_price: float,
        ask_price: float,
        bid_size: Decimal,
        ask_size: Decimal,
        bid_ask_tick_attribute: TickAttribBidAsk,
    ) -> None:
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#receive-tick-data"""
        tick = BidAskTick(
            tick_type=TickType.BID_ASK,
            time=time,
            bid_price=bid_price,
            ask_price=ask_price,
            bid_size=bid_size,
            ask_size=ask_size,
            bid_past_low=bid_ask_tick_attribute.bidPastLow,
            ask_past_high=bid_ask_tick_attribute.askPastHigh,
        )
        self._store_realtime_response(request_id, tick)

    def _on_tick_by_tick_midpoint(
        self,
        request_id: int,
        time: int,
        midpoint: float,
    ) -> None:
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#receive-tick-data"""
        tick = MidpointTick(
            tick_type=TickType.MID_POINT,
            time=time,
            midpoint=midpoint,
        )
        self._store_realtime_response(request_id, tick)

    def request_realtime_bars(
        self,
        request: RealtimeBarRequest,
    ) -> None:
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#request-live-bars"""
        self.client.reqRealTimeBars(
            reqId=request.request_id,
            contract=request.contract,
            barSize=request.bar_size,
            whatToShow=request.bar_type.value,
            useRTH=not request.extended_hours,
            realTimeBarsOptions=[],
        )

    def cancel_realtime_bars(self, request_id: int) -> None:
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#cancel-live-bars"""
        self.client.cancelRealTimeBars(request_id)

    def _on_realtime_bar(
        self,
        request_id: int,
        time: int,
        open_: float,
        high: float,
        low: float,
        close: float,
        volume: Decimal,
        weighted_average_price: Decimal,
        count: int,
    ) -> None:
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#receive-live-bars"""
        bar = Bar(time, open_, high, low, close, volume, weighted_average_price, count)
        self._store_realtime_response(request_id, bar)

    def _initialize_keep_up_to_date_bars(self, key: int, window_length: int = 10) -> None:
        with self._lock:
            self._responses[key] = MarketDataRequestManager(window_length)

    def _store_keep_up_to_date_bar(self, key: int, response: Bar) -> None:
        request_manager = self._responses[key]
        with request_manager.lock:
            if response.time == request_manager.response[-1].time:
                request_manager.response.pop()
                request_manager.response.append(response)
            else:
                request_manager.response.append(response)

    def request_historical_data(
        self,
        request: HistoricalDataRequest,
        window_length: int = 10,
    ) -> list[Bar] | None:
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#request-historical-data"""
        LOGGER.info(f"Requesting historical data: {request}")
        if request.keep_up_to_date:
            self._initialize_keep_up_to_date_bars(request.request_id, window_length)
            self.client.reqHistoricalData(
                reqId=request.request_id,
                contract=request.contract,
                endDateTime=request.end_datetime.strftime("%Y%m%d %H:%M:%S %Z") if request.end_datetime else "",
                durationStr=request.time_period,
                barSizeSetting=request.bar_size,
                whatToShow=request.bar_type.value,
                useRTH=not request.extended_hours,
                formatDate=request.date_format.value,
                keepUpToDate=request.keep_up_to_date,
                chartOptions=[],
            )
            return None
        else:
            self._initialize_chain_response(request.request_id)
            self.client.reqHistoricalData(
                reqId=request.request_id,
                contract=request.contract,
                endDateTime=request.end_datetime.strftime("%Y%m%d %H:%M:%S %Z") if request.end_datetime else "",
                durationStr=request.time_period,
                barSizeSetting=request.bar_size,
                whatToShow=request.bar_type.value,
                useRTH=not request.extended_hours,
                formatDate=request.date_format.value,
                keepUpToDate=request.keep_up_to_date,
                chartOptions=[],
            )
            response = self._wait_for_response(request.request_id)
            self._delete_response(request.request_id)
            return response

    def cancel_historical_data(self, request_id: int) -> None:
        self.client.cancelHistoricalData(request_id)

    def fetch_historical_data(self, request_id: int) -> list[Bar]:
        with self._responses[request_id].lock:
            return list(self._responses[request_id].response)

    def _on_historical_data(
        self,
        request_id: int,
        bar: BarData,
    ) -> None:
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#receiving-historical-bars"""
        date_string, timezone_string = bar.date.rsplit(" ", 1)
        bar = Bar(
            time=datetime.strptime(date_string, "%Y%m%d %H:%M:%S")
            .replace(tzinfo=ZoneInfo(timezone_string))
            .astimezone(ZoneInfo("UTC")),
            open_=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
            weighted_average_price=bar.wap,
            count=bar.barCount,
        )

        self._store_chain_response(request_id, bar)

    def _on_historical_data_update(
        self,
        request_id: int,
        bar: BarData,
    ) -> None:
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#receiving-historical-bars"""
        date_string, timezone_string = bar.date.rsplit(" ", 1)
        bar = Bar(
            time=datetime.strptime(date_string, "%Y%m%d %H:%M:%S")
            .replace(tzinfo=ZoneInfo(timezone_string))
            .astimezone(ZoneInfo("UTC")),
            open_=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
            weighted_average_price=bar.wap,
            count=bar.barCount,
        )

        self._store_keep_up_to_date_bar(request_id, bar)

    def _on_historical_data_end(
        self,
        request_id: int,
        start: str,
        end: str,
    ) -> None:
        self._end_chain_response(request_id)

    def request_scanner_parameters(self) -> None:
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#request-scanner-parameters"""
        self.client.reqScannerParameters()

    def _on_scanner_parameters(self, xml: str) -> None:
        scanner_params_path = os.path.join(os.path.dirname(__file__), "../..", "scanner_parameters.xml")
        scanner_params_path = os.path.abspath(scanner_params_path)
        with open(scanner_params_path, "w") as f:
            f.write(xml)
        LOGGER.info("Received scanner parameters.")

    def request_scanner(
        self,
        request: ScannerRequest,
    ) -> None:
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#request-scanner-subscription"""
        self._initialize_realtime_response(
            request.request_id,
            window_length=request.subscription.numberOfRows if request.subscription.numberOfRows != -1 else 50,
        )
        self.client.reqScannerSubscription(request.request_id, request.subscription, [], request.filters)

    def cancel_scanner(self, request_id: int) -> None:
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#cancel-scanner-subscription"""
        self.client.cancelScannerSubscription(request_id)

    def fetch_scanner_data(self, request_id: int) -> list[ScannerData]:
        return self.fetch_realtime_response(request_id)

    def _on_scanner_data(
        self,
        request_id: int,
        rank: int,
        contract_details: ContractDetails,
        distance: str,
        benchmark: str,
        projection: str,
        legs_str: str,
    ) -> None:
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#receive-scanner-data"""
        scanner_data = ScannerData(rank, contract_details, legs_str)
        self._store_realtime_response(request_id, scanner_data)

    def _on_scanner_data_end(
        self,
        request_id: int,
    ) -> None:
        LOGGER.info(f"Received scanner data end: {request_id}")
