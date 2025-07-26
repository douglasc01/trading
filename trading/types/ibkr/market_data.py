from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from ibapi.contract import ContractDetails


class TickType(str, Enum):
    LAST = "Last"
    ALL_LAST = "AllLast"
    BID_ASK = "BidAsk"
    MID_POINT = "MidPoint"


@dataclass
class TradeTick:
    tick_type: TickType
    time: int
    price: float
    size: Decimal
    past_limit: bool
    unreported: bool
    exchange: str
    special_conditions: str


@dataclass
class BidAskTick:
    tick_type: TickType
    time: int
    bid_price: float
    ask_price: float
    bid_size: Decimal
    ask_size: Decimal
    bid_past_low: bool
    ask_past_high: bool


@dataclass
class MidpointTick:
    tick_type: TickType
    time: int
    midpoint: float


@dataclass
class Bar:
    time: int | datetime
    open_: float
    high: float
    low: float
    close: float
    volume: Decimal | float
    weighted_average_price: Decimal | float
    count: int

    def __repr__(self) -> str:
        return (
            f"Bar(time={self.time}, open_={self.open_}, high={self.high}, low={self.low}, close={self.close}, "
            f"volume={self.volume}, wap={self.weighted_average_price}, count={self.count})"
        )


@dataclass
class ScannerData:
    rank: int
    contract_details: ContractDetails
    legs_str: str
