"""Balance and allowance management"""

from typing import Optional, Any
from py_clob_client.clob_types import BalanceAllowanceParams, AssetType
from src.utils.logger import log
from .client import client
from src.utils.web3_utils import approve_usdc
from src.config.settings import EXCHANGE_ADDRESS


def get_balance_allowance(token_id: Optional[str] = None) -> Optional[dict]:
    """Get balance and allowance"""
    try:
        atype: Any = AssetType.CONDITIONAL if token_id else AssetType.COLLATERAL
        params: Any = BalanceAllowanceParams(asset_type=atype, token_id=token_id or "")
        result: Any = client.get_balance_allowance(params)
        if isinstance(result, dict):
            return {
                "balance": float(result.get("balance", 0)) / 1_000_000.0,
                "allowance": float(result.get("allowance", 0)) / 1_000_000.0,
            }
        elif (
            result is not None
            and hasattr(result, "balance")
            and hasattr(result, "allowance")
        ):
            return {
                "balance": float(getattr(result, "balance")) / 1_000_000.0,
                "allowance": float(getattr(result, "allowance")) / 1_000_000.0,
            }
        return None
    except Exception as e:
        log(f"⚠️  Error getting balance/allowance: {e}")
        return None


def ensure_allowance(required_amount: float) -> bool:
    """Ensure USDC allowance is sufficient, trigger approval if not"""
    info = get_balance_allowance()
    if not info:
        return False

    allowance = info.get("allowance", 0)
    if allowance < required_amount:
        log(
            f"👀 Current USDC allowance (${allowance:.2f}) < required (${required_amount:.2f})"
        )
        # Approve a large amount to avoid frequent approvals
        # Default to $1,000,000 or 10x required if that's somehow larger
        approve_amount = max(1_000_000.0, required_amount * 10)
        return approve_usdc(EXCHANGE_ADDRESS, approve_amount)

    return True
