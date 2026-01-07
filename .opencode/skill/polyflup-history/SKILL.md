---
name: polyflup-history
description: Chronological log of system improvements and session summaries for PolyFlup.
---

## Session Improvements Summary

### 2026-01-07
- **Graceful Post-Only Rejection Handling**: Implemented automatic single-retry for limit orders that fail due to crossing the spread. The retry adjusts the price by ±0.0001. Added `is_post_only_rejection` utility.
- **Heartbeat Implementation**: Added 30-second `client.heartbeat()` calls to the main loop in `src/bot.py` for API connection stability.
- **Pre-flight Allowance Guardrails**: Added USDC allowance checks in `place_batch_orders` to prevent 400 errors from the API when allowance is insufficient.
- **Architectural Refactor**: Moved `get_balance_allowance` to `src/trading/orders/balances.py` to resolve circular dependency issues between limit and position modules.
- **Sizing Safety**: Implemented strict USDC balance snapshotting at the start of every 15-minute window. All sizing calculations now use this snapshot to ensure consistency and prevent over-allocation.
- **Strict Exposure Cap**: Enforced a hard 20% cap per symbol (initial + scale-ins) relative to the window's starting balance.
- **Scale-In Trimming**: Added logic to automatically trim scale-in order sizes if they would exceed the 20% cap. Orders resulting in < 5.0 shares are skipped entirely.
- **Stop-Loss Reliability**: Added explicit `cancel_market_orders(asset_id)` calls and a 1.5s wait before stop-loss or reversal sells to unlock tokens held by exit plans or other limit orders, preventing "Insufficient funds" errors.
- **Knowledge Update**: Added Polymarket Maker Rebates and Taker Fee details to `polymarket-trading` skill. Noted that taker fees are token-based for BUYS and USDC-based for SELLS, with higher effective rates for low-price sells.
- **Scale-In**: Enhanced with confidence-weighted dynamic timing. Expanded default window to 7.5m (450s) and implemented tiered early entry (up to 12m) for high-confidence (>=90%) and high-price (>=0.80) winners.
- **Precision**: Reduced balance sync threshold to 0.0001.
- **Min Size**: Added pre-flight check for 5.0 share minimum.
- **Stability**: Fixed NoneType safety in P&L summing and bet calculation.

### 2026-01-06
- **Deadlocks**: Fixed "database is locked" errors by passing active cursors to write functions.
- **Duplicate Protection**: Added `has_side_for_window()` check to prevent over-leveraging.
- **Stop Loss**: Implemented "Triple Check" Reversal-First stop loss (Hedge duration > 120s, confidence > 30%, absolute floor $0.15).
- **Logging**: Implemented window-specific log files.

### 2026-01-05
- **WebSocket**: Replaced polling with real-time WebSocketManager for prices and user updates.
- **Modularity**: Full refactor of `src/trading/orders` and `src/data/market_data` into packages.
- **Audit**: Integrated Data API for automated settlement auditing.
