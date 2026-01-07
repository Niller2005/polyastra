"""Balance and allowance management"""

from typing import Optional, Any
from py_clob_client.clob_types import BalanceAllowanceParams, AssetType
from src.utils.logger import log, log_error
from .client import client


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
        emsg = str(e)
        if "rate limit" in emsg.lower():
            # Don't spam rate limit errors
            return None
        log_error(f"⚠️  Error getting balance/allowance: {e}", include_traceback=False)
        return None
