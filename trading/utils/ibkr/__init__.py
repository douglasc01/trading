from typing import Literal

from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.scanner import ScannerSubscription


def create_stock_contract(symbol: str) -> Contract:
    """
    Creates and returns a contract for a given stock symbol.
    Automatically sets the location code to the US major exchanges.
    Automatically sets the instrument type to stock.
    Automatically sets the exchange to SMART.
    Automatically sets the currency to USD.

    Arguments:
        symbol: str
            The symbol of the stock to create a contract for.

    Returns:
        Contract: A contract object for the given stock symbol.
    """
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.currency = "USD"
    return contract


def create_simple_order(
    action: Literal["BUY", "SELL"], quantity: float, limit_price: float | None = None, extended_hours: bool = False
) -> Order:
    """
    Creates and returns an order object for a given buy/sell action for market/limit orders with a basic configuration.

    Arguments:
        action: Literal["BUY", "SELL"]
            The action to take on the order.
        quantity: float
            The quantity of the order.
        limit_price: float | None
            The price to limit the order at.
        extended_hours: bool
            Whether the order can be executed during extended hours.

    Returns:
        Order: An order object for the given buy/sell action for market/limit orders with a basic configuration.
    """
    order = Order()
    order.action = action
    order.totalQuantity = quantity
    order.orderType = "LMT" if limit_price else "MKT"
    if limit_price:
        order.lmtPrice = limit_price
    order.outsideRth = extended_hours
    return order


def create_bracket_order(
    parent_order_id: int,
    action: Literal["BUY", "SELL"],
    quantity: float,
    take_profit_price: float,
    stop_loss_price: float,
    limit_price: float | None = None,
    extended_hours: bool = False,
) -> list[Order]:
    parent_order = Order()
    parent_order.orderId = parent_order_id
    parent_order.action = action
    parent_order.totalQuantity = quantity
    parent_order.orderType = "LMT" if limit_price else "MKT"
    if limit_price:
        parent_order.lmtPrice = limit_price
    parent_order.outsideRth = extended_hours
    parent_order.transmit = False

    take_profit_order = Order()
    take_profit_order.orderId = parent_order_id + 1
    take_profit_order.action = "SELL" if action == "BUY" else "BUY"
    take_profit_order.totalQuantity = quantity
    take_profit_order.orderType = "LMT" if limit_price else "MIT"
    if limit_price:
        take_profit_order.lmtPrice = take_profit_price
    else:
        take_profit_order.auxPrice = take_profit_price
    take_profit_order.parentId = parent_order_id
    take_profit_order.transmit = False

    stop_loss_order = Order()
    stop_loss_order.orderId = parent_order_id + 2
    stop_loss_order.action = "SELL" if action == "BUY" else "BUY"
    stop_loss_order.totalQuantity = quantity
    stop_loss_order.orderType = "STP"
    stop_loss_order.auxPrice = stop_loss_price
    stop_loss_order.parentId = parent_order_id
    stop_loss_order.transmit = True

    return [parent_order, take_profit_order, stop_loss_order]


def create_scanner_subscription(
    instrument: str = "STK",
    location_code: str = "STK.US.MAJOR",
    scan_code: str = "MOST_ACTIVE",
    above_price: float | None = None,
    below_price: float | None = None,
    above_volume: float | None = None,
    above_market_cap: float | None = None,
    below_market_cap: float | None = None,
    number_of_rows: int = 50,
) -> ScannerSubscription:
    """
    Helper function to create a scanner subscription.

    Arguments:
        instrument: str
            The instrument to scan for.
        location_code: str
            The location code to scan for.
        scan_code: str
            The scan code to scan for.
        above_price: float | None
            The price to scan for above.
        below_price: float | None
            The price to scan for below.
        above_volume: float | None
            The volume to scan for above.
        above_market_cap: float | None
            The market cap to scan for above.
        below_market_cap: float | None
            The market cap to scan for below.
        number_of_rows: int
            The top n results to return.

    Returns:
        ScannerSubscription: A scanner subscription object.
    """
    scanner_subscription = ScannerSubscription()
    scanner_subscription.instrument = instrument
    scanner_subscription.locationCode = location_code
    scanner_subscription.scanCode = scan_code
    if below_price:
        scanner_subscription.belowPrice = below_price
    if above_price:
        scanner_subscription.abovePrice = above_price
    if above_volume:
        scanner_subscription.aboveVolume = above_volume
    if above_market_cap:
        scanner_subscription.marketCapAbove = above_market_cap
    if below_market_cap:
        scanner_subscription.marketCapBelow = below_market_cap
    scanner_subscription.numberOfRows = number_of_rows
    return scanner_subscription
