from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.scanner import ScannerSubscription
from ibapi.tag_value import TagValue

from trading.types.ibkr.market_data import TickType


@dataclass
class TickByTickDataRequest:
    request_id: int
    contract: Contract
    tick_type: TickType
    number_of_ticks: int
    ignore_change_in_size: bool


class BarType(str, Enum):
    TRADES = "TRADES"
    BID = "BID"
    ASK = "ASK"
    MIDPOINT = "MIDPOINT"


class DateFormat(int, Enum):
    FULL_DATE_TIME = 1
    EPOCH = 2
    MONTH_DAY_TIME = 3


@dataclass
class RealtimeBarRequest:
    request_id: int
    contract: Contract
    bar_size: int
    bar_type: BarType
    extended_hours: bool


@dataclass
class HistoricalDataRequest:
    """
    See the following for time period and bar size options:
    https://ibkrcampus.com/campus/ibkr-api-page/twsapi-doc/#hist-duration

    See the following for date format options:
    https://ibkrcampus.com/campus/ibkr-api-page/twsapi-doc/#hist-format-date
    """

    request_id: int
    contract: Contract
    time_period: str
    bar_size: str
    bar_type: BarType
    end_datetime: datetime | None = field(default=None)
    date_format: DateFormat = field(default=DateFormat.FULL_DATE_TIME)
    keep_up_to_date: bool = field(default=False)
    extended_hours: bool = field(default=False)


@dataclass
class ScannerRequest:
    request_id: int
    subscription: ScannerSubscription
    filters: list[TagValue] = field(default_factory=list)


@dataclass
class OrderRequest:
    request_id: int
    contract: Contract
    order: Order
