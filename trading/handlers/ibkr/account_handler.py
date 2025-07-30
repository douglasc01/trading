import copy
import logging
import threading
from collections import defaultdict
from decimal import Decimal

from ibapi.client import EClient
from ibapi.contract import Contract

from trading.handlers.ibkr import Handler
from trading.types.ibkr.account import PositionData

LOGGER = logging.getLogger("account-handler")


class PositionManager:
    def __init__(self) -> None:
        self.position_data: PositionData
        self.lock = threading.Lock()


class AccountHandler(Handler):
    def __init__(self, client: EClient) -> None:
        super().__init__(client)
        self._positions: defaultdict[int, PositionManager] = defaultdict(PositionManager)

    def request_realtime_positions(self) -> None:
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#request-positions"""
        self.client.reqPositions()

    def fetch_positions(self) -> dict[int, PositionData]:
        """
        Returns a snapshot of the current positions as a dictionary of contract id to position data

        Returns:
            dict[int, PositionData]: A dictionary of contract id to position data
        """
        with self._lock:
            items = list(self._positions.items())
        return {contract_id: copy.deepcopy(position_manager.position_data) for contract_id, position_manager in items}

    def fetch_positions_by_contract_id(self, contract_id: int) -> PositionData:
        """
        Returns the position data for a given contract id

        Args:
            contract_id (int): The contract id to fetch the position data for

        Returns:
            PositionData: The position data for the given contract id
        """
        with self._positions[contract_id].lock:
            return copy.deepcopy(self._positions[contract_id].position_data)

    def _on_position(
        self,
        account: str,
        contract: Contract,
        position: Decimal,
        avg_cost: float,
    ) -> None:
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#request-positions"""
        with self._positions[contract.conId].lock:
            self._positions[contract.conId].position_data = PositionData(
                account=account,
                contract=contract,
                position=position,
                avg_cost=avg_cost,
            )
