import logging

from ibapi.client import EClient
from ibapi.contract import Contract, ContractDetails

from trading.handlers.ibkr import Handler

LOGGER = logging.getLogger("root-handler")


class BaseHandler(Handler):
    def __init__(self, client: EClient) -> None:
        super().__init__(client)

    def _on_connect_ack(self) -> None:
        LOGGER.info("Connected to TWS")

    def request_ids(self, quantity: int) -> int:
        self.client.reqIds(quantity)
        return self._wait_for_response(-1)

    def _on_next_valid_id(self, order_id: int) -> None:
        LOGGER.info(f"Next valid id: {order_id}")
        self._store_response(-1, order_id)

    def request_contract_details(self, contract: Contract) -> list[ContractDetails]:
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#request-contract-details"""
        contract_details_request_id = -2
        self._initialize_chain_response(contract_details_request_id)
        self.client.reqContractDetails(contract_details_request_id, contract)
        response = self._wait_for_response(contract_details_request_id)
        self._delete_response(contract_details_request_id)
        return response

    def _on_contract_details(self, request_id: int, contract_details: ContractDetails) -> None:
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#request-contract-details"""
        self._store_chain_response(request_id, contract_details)

    def _on_contract_details_end(self, request_id: int) -> None:
        """https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#request-contract-details"""
        self._end_chain_response(request_id)
