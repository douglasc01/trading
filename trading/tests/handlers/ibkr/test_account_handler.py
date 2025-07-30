from decimal import Decimal
from unittest.mock import Mock

import pytest
from ibapi.client import EClient
from ibapi.contract import Contract

from trading.handlers.ibkr.account_handler import AccountHandler
from trading.types.ibkr.account import PositionData


class TestAccountHandler:
    @pytest.fixture
    def mock_client(self) -> Mock:
        return Mock(spec=EClient)

    @pytest.fixture
    def account_handler(self, mock_client: Mock) -> AccountHandler:
        return AccountHandler(mock_client)

    @pytest.fixture
    def mock_contract(self) -> Mock:
        contract = Mock(spec=Contract)
        contract.conId = 123
        return contract

    @pytest.fixture
    def sample_position_data(self, mock_contract: Mock) -> PositionData:
        return PositionData(account="DU123456", contract=mock_contract, position=Decimal("100"), avg_cost=150.50)

    def test_init(self, mock_client: Mock) -> None:
        handler = AccountHandler(mock_client)
        assert handler.client == mock_client
        assert hasattr(handler, "_positions")
        assert hasattr(handler, "_lock")

    def test_request_realtime_positions(self, account_handler: AccountHandler, mock_client: Mock) -> None:
        account_handler.request_realtime_positions()
        mock_client.reqPositions.assert_called_once()

    def test_fetch_positions_empty(self, account_handler: AccountHandler) -> None:
        positions = account_handler.fetch_positions()
        assert positions == {}

    def test_fetch_positions_with_data(
        self, account_handler: AccountHandler, mock_contract: Mock, sample_position_data: PositionData
    ) -> None:
        with account_handler._positions[mock_contract.conId].lock:
            account_handler._positions[mock_contract.conId].position_data = sample_position_data

        positions = account_handler.fetch_positions()
        assert len(positions) == 1
        stored_data = positions[mock_contract.conId]
        assert stored_data.account == sample_position_data.account
        assert stored_data.position == sample_position_data.position
        assert stored_data.avg_cost == sample_position_data.avg_cost

    def test_fetch_positions_by_contract_id(
        self, account_handler: AccountHandler, mock_contract: Mock, sample_position_data: PositionData
    ) -> None:
        with account_handler._positions[mock_contract.conId].lock:
            account_handler._positions[mock_contract.conId].position_data = sample_position_data

        result = account_handler.fetch_positions_by_contract_id(mock_contract.conId)
        assert result.account == sample_position_data.account
        assert result.position == sample_position_data.position
        assert result.avg_cost == sample_position_data.avg_cost

    def test_fetch_positions_by_contract_id_not_found(self, account_handler: AccountHandler) -> None:
        with pytest.raises(AttributeError):
            account_handler.fetch_positions_by_contract_id(999)

    def test_on_position(self, account_handler: AccountHandler, mock_contract: Mock) -> None:
        account = "DU123456"
        position = Decimal("50")
        avg_cost = 145.75

        account_handler._on_position(account, mock_contract, position, avg_cost)

        with account_handler._positions[mock_contract.conId].lock:
            stored_data = account_handler._positions[mock_contract.conId].position_data
            assert stored_data.account == account
            assert stored_data.contract == mock_contract
            assert stored_data.position == position
            assert stored_data.avg_cost == avg_cost

    def test_on_position_updates_existing(
        self, account_handler: AccountHandler, mock_contract: Mock, sample_position_data: PositionData
    ) -> None:
        with account_handler._positions[mock_contract.conId].lock:
            account_handler._positions[mock_contract.conId].position_data = sample_position_data

        new_position = Decimal("75")
        new_avg_cost = 160.25

        account_handler._on_position("DU123456", mock_contract, new_position, new_avg_cost)

        with account_handler._positions[mock_contract.conId].lock:
            stored_data = account_handler._positions[mock_contract.conId].position_data
            assert stored_data.position == new_position
            assert stored_data.avg_cost == new_avg_cost

    def test_fetch_positions_thread_safety(
        self, account_handler: AccountHandler, mock_contract: Mock, sample_position_data: PositionData
    ) -> None:
        import threading

        with account_handler._positions[mock_contract.conId].lock:
            account_handler._positions[mock_contract.conId].position_data = sample_position_data

        results: list[dict[int, PositionData]] = []
        errors: list[Exception] = []

        def fetch_positions() -> None:
            try:
                result = account_handler.fetch_positions()
                results.append(result)
            except Exception as e:
                errors.append(e)

        threads = []
        for _ in range(5):
            thread = threading.Thread(target=fetch_positions)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(results) == 5
        for result in results:
            assert len(result) == 1
