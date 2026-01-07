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

- **Balance Snapshotting**: Use the snapshotted USDC balance (taken at the start of the 15m window) for all sizing calculations to maintain consistency.
- **Strict 20% Cap**: No single symbol's total exposure (initial entry + scale-ins) may exceed 20% of the snapshotted balance.
- **Scale-in Trimming**: If a scale-in would exceed the 20% cap, it MUST be trimmed to fit. If the resulting size is < 5.0 shares, skip the trade.
- **Stop-Loss Reliability**: ALWAYS call `cancel_market_orders(asset_id)` for the specific asset before executing a stop-loss or reversal sell to ensure tokens are unlocked.

