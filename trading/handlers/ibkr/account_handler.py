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

    def fetch_positions(self) -> dict[int, PositionData]:
        with self._lock:
            return {
                contract_id: copy.deepcopy(position_manager.position_data)
                for contract_id, position_manager in self._positions.items()
            }

    def fetch_positions_by_contract_id(self, contract_id: int) -> PositionData:
        with self._positions[contract_id].lock:
            return copy.deepcopy(self._positions[contract_id].position_data)
