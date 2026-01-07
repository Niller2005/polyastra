---
name: python-bot-standards
description: Coding standards, modular architecture, and common execution patterns for the PolyFlup Python backend.
---

## Python Coding Standards

### Modular Architecture
The backend is modularized into packages:
- `src.trading.orders`: Order management (limit, market, batch, positions).
- `src.data.market_data`: Data fetching (polymarket, binance, indicators).
- `src.trading`: Centralized execution logic (`execution.py`, `logic.py`).

### Standard Trade Execution
```python
from src.trading import execute_trade
# Execute a trade with full tracking and notifications
trade_id = execute_trade(trade_params, is_reversal=False)
```

### Imports
- Use absolute imports from `src.*`
- Group imports: standard library → third-party → local

### Formatting
- **Indentation**: 4 spaces
- **Line length**: ~90 characters
- **Strings**: Double quotes preferred
- **Docstrings**: Triple double-quotes with brief description

### Error Handling & Logging
- Use `log_error(text, include_traceback=True)` from `src.utils.logger` for all exceptions.
- Always log errors with context: `log(f"[{symbol}] Order failed: {e}")`.
- Graceful degradation: return neutral/safe values on error.
- Use emojis in logs (👀 Monitoring, 🚀 Execution, ✅ Success, ❌ Error).

## Sizing & Safety Mandates

- **Tick Size & Precision**: `MIN_TICK_SIZE` is set to `0.0001`. Use this for all price adjustments and rounding.
- **Graceful Post-Only Handling**: Limit orders that fail with a "Post-Only" violation (crossing the spread) should automatically retry once with a price adjustment of ±0.0001. Use `is_post_only_rejection(error_str)` from `src.trading.orders.utils` to identify these cases.
- **Pre-flight Allowance Guardrails**: `place_batch_orders` performs a pre-flight check against the USDC allowance before sending orders to the API to prevent `PolyApiException 400` errors.
- **Balance Snapshotting**: Use the snapshotted USDC balance (taken at the start of the 15m window) for all sizing calculations to maintain consistency.
- **Strict 20% Cap**: No single symbol's total exposure (initial entry + scale-ins) may exceed 20% of the snapshotted balance.
- **Scale-in Trimming**: If a scale-in would exceed the 20% cap, it MUST be trimmed to fit. If the resulting size is < 5.0 shares, skip the trade.
- **Stop-Loss Reliability**: ALWAYS call `cancel_market_orders(asset_id)` for the specific asset before executing a stop-loss or reversal sell to ensure tokens are unlocked.

## Common Code Patterns

### Heartbeat
The main loop in `src/bot.py` calls `client.post_heartbeat(None)` every 30 seconds to maintain stable API connections.

### USDC Allowance
The bot automatically manages its USDC allowance. `ensure_allowance(required_amount)` in `src.trading.orders.balances` will trigger an on-chain `approve` transaction via `src.utils.web3_utils.approve_usdc` if the current allowance is insufficient.

### Balance & Allowance
`get_balance_allowance(token_id=None)` has been moved to `src.trading.orders.balances` to break circular dependencies. Always import from there.

