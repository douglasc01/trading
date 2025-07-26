from dataclasses import dataclass
from decimal import Decimal

from ibapi.contract import Contract


@dataclass
class PositionData:
    account: str
    contract: Contract
    position: Decimal
    avg_cost: float

    def __repr__(self) -> str:
        return (
            f"PositionData(account={self.account}, contract={self.contract}, position={self.position}, "
            f"avg_cost={self.avg_cost})"
        )
