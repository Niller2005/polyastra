---
name: polymarket-trading
description: Polymarket-specific terminology, trading strategies, and API reference.
---

## Terminology & Concepts

- **Exit Plan**: Automated limit sell at $0.99 placed as soon as position opens.
- **Hedged Reversal**: Holding both UP and DOWN positions simultaneously when trend flips.
- **Midpoint Stop Loss**: Market sell triggered by midpoint price dropping to/below $0.30.
- **Scale-In**: Adding capital to winning positions via Market Orders (FAK).
- **Underdog**: Side trading below $0.50. Requires >40% confidence for entry.
- **Tick Size**: Minimum price increment allowed for a market (e.g., 0.01 or 0.001).

## Strategy Nuances
- **Sizing Consistency**: Sizing is calculated against a USDC balance snapshot taken at the **exact start** of each 15-minute window.
- **Exposure Limits**:
    - **Strict 20% Cap**: No symbol can exceed 20% of the window's starting balance.
    - **Trimming**: Scale-in orders are automatically trimmed to stay within this cap.
- **Scale-In Strategy (Dynamic)**:
    - Default `SCALE_IN_TIME_LEFT`: 450s (7.5 minutes).
    - Dynamic entry timing based on confidence (`edge`) and midpoint price:
        - 12m left: `edge` >= 90% and price >= $0.80.
        - 9m left: `edge` >= 80% and price >= $0.70.
        - 7m left: `edge` >= 70% and price >= $0.65.
- **Trend Agreement Bonus**: 1.1x multiplier if Binance and Polymarket trends align.
- **Lead/Lag Bonus**: 1.2x bonus or 0.8x penalty based on cross-exchange consistency.
- **Precision**: Use strict 0.0001 threshold for balance syncing.
- **Minimum Size**: Polymarket enforces a 5.0 share minimum for ALL limit orders. If trimming a scale-in results in < 5.0 shares, the order is cancelled.

## Fees & Rebates (15-Minute Crypto Markets)

- **Taker Fees**: Applied ONLY to 15-minute crypto markets.
- **Fee Deduction**: 
    - **BUY**: Fee is taken in **Tokens** from the proceeds.
    - **SELL**: Fee is taken in **USDC** from the proceeds.
- **Effective Rates**: 
    - **Buying**: Peaks at ~1.6% at $0.50 price.
    - **Selling**: Peaks at ~3.7% at $0.30 price. Selling is generally more expensive because USDC is taken directly.
- **Fee Precision**: Rounded to 4 decimal places (min 0.0001 USDC). Small trades at extremes might be fee-free.
- **Maker Rebates**: Distributed daily in USDC to makers who provide liquidity that gets filled.
- **Strategy Implications**: 
    - Prefer **Maker orders** (Limit orders that add liquidity) to avoid fees and potentially earn rebates.
    - Selling at low prices as a taker is particularly costly.

## Common Code Patterns

### Market Data
```python
from src.trading.orders import get_midpoint, get_spread, check_liquidity
# Get accurate midpoint price
price = get_midpoint(token_id)
# Check if liquidity is good
if check_liquidity(token_id, size=100, warn_threshold=0.05):
    # Safe to trade
```

### Order Placement
```python
from src.trading.orders import place_batch_orders, place_market_order, cancel_market_orders
# Batch Orders
results = place_batch_orders(orders)
# Market Sell (Stop Loss) - Always cancel existing orders for asset first
cancel_market_orders(token_id)
result = place_market_order(token_id, amount=10.0, side="SELL", order_type="FAK")
```

## Standard Emoji Guide
- 👀 Monitoring
- 📈 Positive P&L / Scaling In
- 📉 Negative P&L / Exit plan
- 🛑 Stop loss triggered
- 🎯 Take profit filled
- ✅ Success / Order filled
- ❌ Error/Failure
- ⚠️ Warning
- 🔄 Reversal / Retry
- 🚀 Trade execution
- 💰 Money/Balance
