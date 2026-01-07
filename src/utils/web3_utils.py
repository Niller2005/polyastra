"""Web3 utilities for blockchain interactions"""

from web3 import Web3
from eth_account import Account
from src.config.settings import (
    POLYGON_RPC,
    USDC_ADDRESS,
    PROXY_PK,
)
from src.utils.logger import log, log_error


w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))


def get_balance(addr: str) -> float:
    """Get USDC balance for address"""
    try:
        abi = '[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"}]'
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(USDC_ADDRESS), abi=abi
        )
        raw = contract.functions.balanceOf(Web3.to_checksum_address(addr)).call()
        return raw / 1e6
    except Exception:
        return 0.0
