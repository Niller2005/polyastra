"""Helpers for ensuring and maintaining the normalized database schema."""

from __future__ import annotations

from typing import Iterable

WINDOWS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS windows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    slug TEXT,
    window_start TEXT NOT NULL,
    window_end TEXT,
    token_id TEXT,
    status TEXT NOT NULL DEFAULT 'OPEN',
    settled BOOLEAN NOT NULL DEFAULT 0,
    settled_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);"""

WINDOWS_INDEXES: tuple[str, ...] = (
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_windows_symbol_start ON windows(symbol, window_start)",
    "CREATE INDEX IF NOT EXISTS idx_windows_status ON windows(status)",
)

POSITIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS positions (
    trade_id INTEGER PRIMARY KEY,
    window_id INTEGER,
    symbol TEXT NOT NULL,
    side TEXT,
    token_id TEXT,
    entry_price REAL,
    size REAL,
    bet_usd REAL,
    p_yes REAL,
    best_bid REAL,
    best_ask REAL,
    imbalance REAL,
    funding_bias REAL,
    order_status TEXT,
    order_id TEXT,
    limit_sell_order_id TEXT,
    scale_in_order_id TEXT,
    target_price REAL,
    is_reversal BOOLEAN NOT NULL DEFAULT 0,
    reversal_triggered BOOLEAN NOT NULL DEFAULT 0,
    reversal_triggered_at TEXT,
    last_scale_in_at TEXT,
    final_outcome TEXT,
    exit_price REAL,
    pnl_usd REAL,
    roi_pct REAL,
    settled BOOLEAN NOT NULL DEFAULT 0,
    settled_at TEXT,
    exited_early BOOLEAN NOT NULL DEFAULT 0,
    scaled_in BOOLEAN NOT NULL DEFAULT 0,
    entry_timestamp TEXT,
    window_start TEXT,
    window_end TEXT,
    status TEXT NOT NULL DEFAULT 'OPEN',
    FOREIGN KEY(window_id) REFERENCES windows(id),
    FOREIGN KEY(trade_id) REFERENCES trades(id) ON DELETE CASCADE
);"""

POSITIONS_INDEXES: tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS idx_positions_window ON positions(window_id)",
    "CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)",
    "CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)",
)

ORDERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER NOT NULL,
    window_id INTEGER,
    symbol TEXT NOT NULL,
    order_id TEXT NOT NULL,
    order_role TEXT NOT NULL,
    side TEXT NOT NULL,
    price REAL,
    size REAL,
    bet_usd REAL,
    status TEXT NOT NULL DEFAULT 'UNKNOWN',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(trade_id) REFERENCES trades(id) ON DELETE CASCADE,
    FOREIGN KEY(window_id) REFERENCES windows(id),
    UNIQUE(order_id)
);"""

ORDERS_INDEXES: tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS idx_orders_trade ON orders(trade_id)",
    "CREATE INDEX IF NOT EXISTS idx_orders_window ON orders(window_id)",
    "CREATE INDEX IF NOT EXISTS idx_orders_role ON orders(order_role)",
)

WINDOW_STATS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS window_stats (
    window_id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    window_start TEXT NOT NULL,
    total_trades INTEGER NOT NULL DEFAULT 0,
    open_positions INTEGER NOT NULL DEFAULT 0,
    settled_positions INTEGER NOT NULL DEFAULT 0,
    gross_exposure REAL NOT NULL DEFAULT 0.0,
    avg_edge REAL NOT NULL DEFAULT 0.0,
    avg_roi REAL NOT NULL DEFAULT 0.0,
    realized_pnl REAL NOT NULL DEFAULT 0.0,
    unrealized_pnl REAL NOT NULL DEFAULT 0.0,
    last_updated TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(window_id) REFERENCES windows(id) ON DELETE CASCADE
);"""

WINDOW_STATS_INDEXES: tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS idx_window_stats_symbol ON window_stats(symbol)",
)

BALANCES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS balances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    window_id INTEGER,
    symbol TEXT,
    snapshot_at TEXT NOT NULL DEFAULT (datetime('now')),
    total_usdc REAL,
    available_usdc REAL,
    exposure_usd REAL,
    exposure_pct REAL,
    share_balance REAL,
    allowance_usdc REAL,
    notes TEXT,
    FOREIGN KEY(window_id) REFERENCES windows(id) ON DELETE SET NULL
);"""

BALANCES_INDEXES: tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS idx_balances_window ON balances(window_id)",
    "CREATE INDEX IF NOT EXISTS idx_balances_symbol ON balances(symbol)",
)

SIGNALS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    window_id INTEGER,
    trade_id INTEGER,
    symbol TEXT,
    signal_name TEXT NOT NULL,
    signal_value REAL,
    confidence REAL,
    metadata TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(window_id) REFERENCES windows(id) ON DELETE SET NULL,
    FOREIGN KEY(trade_id) REFERENCES trades(id) ON DELETE CASCADE,
    UNIQUE(trade_id, signal_name)
);"""

SIGNALS_INDEXES: tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS idx_signals_window ON signals(window_id)",
    "CREATE INDEX IF NOT EXISTS idx_signals_name ON signals(signal_name)",
)

ORDERS_HISTORY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS orders_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    trade_id INTEGER,
    window_id INTEGER,
    symbol TEXT,
    event_type TEXT NOT NULL,
    status_from TEXT,
    status_to TEXT,
    reason TEXT,
    price REAL,
    size REAL,
    bet_usd REAL,
    filled REAL,
    fee REAL,
    metadata TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(trade_id) REFERENCES trades(id) ON DELETE SET NULL,
    FOREIGN KEY(window_id) REFERENCES windows(id) ON DELETE SET NULL
);"""

ORDERS_HISTORY_INDEXES: tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS idx_orders_history_order ON orders_history(order_id)",
    "CREATE INDEX IF NOT EXISTS idx_orders_history_event ON orders_history(event_type)",
)

TRIGGER_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TRIGGER IF NOT EXISTS trg_trades_after_insert_normalized
    AFTER INSERT ON trades
    BEGIN
        INSERT OR IGNORE INTO windows (symbol, slug, window_start, window_end, token_id, status, settled, settled_at, created_at)
        SELECT NEW.symbol, NEW.slug, NEW.window_start, NEW.window_end, NEW.token_id,
               CASE WHEN NEW.settled = 1 THEN 'CLOSED' ELSE 'OPEN' END,
               NEW.settled,
               NEW.settled_at,
               COALESCE(NEW.timestamp, datetime('now'))
        WHERE NEW.window_start IS NOT NULL;

        UPDATE windows
        SET window_end = COALESCE(NEW.window_end, window_end),
            slug = COALESCE(NEW.slug, slug),
            token_id = COALESCE(NEW.token_id, token_id),
            status = CASE WHEN NEW.settled = 1 THEN 'CLOSED' ELSE status END,
            settled = CASE WHEN NEW.settled = 1 THEN 1 ELSE settled END,
            settled_at = CASE WHEN NEW.settled = 1 THEN COALESCE(NEW.settled_at, settled_at) ELSE settled_at END
        WHERE NEW.window_start IS NOT NULL
          AND symbol = NEW.symbol
          AND window_start = NEW.window_start;

        INSERT OR REPLACE INTO positions (
            trade_id, window_id, symbol, side, token_id, entry_price, size, bet_usd,
            p_yes, best_bid, best_ask, imbalance, funding_bias, order_status, order_id,
            limit_sell_order_id, scale_in_order_id, target_price, is_reversal, reversal_triggered,
            reversal_triggered_at, last_scale_in_at, final_outcome, exit_price, pnl_usd, roi_pct,
            settled, settled_at, exited_early, scaled_in, entry_timestamp, window_start, window_end, status
        )
        VALUES (
            NEW.id,
            (CASE WHEN NEW.window_start IS NOT NULL THEN (SELECT id FROM windows WHERE symbol = NEW.symbol AND window_start = NEW.window_start) ELSE NULL END),
            NEW.symbol,
            NEW.side,
            NEW.token_id,
            NEW.entry_price,
            NEW.size,
            NEW.bet_usd,
            NEW.p_yes,
            NEW.best_bid,
            NEW.best_ask,
            NEW.imbalance,
            NEW.funding_bias,
            NEW.order_status,
            NEW.order_id,
            NEW.limit_sell_order_id,
            NEW.scale_in_order_id,
            NEW.target_price,
            NEW.is_reversal,
            NEW.reversal_triggered,
            NEW.reversal_triggered_at,
            NEW.last_scale_in_at,
            NEW.final_outcome,
            NEW.exit_price,
            NEW.pnl_usd,
            NEW.roi_pct,
            NEW.settled,
            NEW.settled_at,
            NEW.exited_early,
            NEW.scaled_in,
            NEW.timestamp,
            NEW.window_start,
            NEW.window_end,
            CASE
                WHEN NEW.settled = 1 THEN 'CLOSED'
                WHEN NEW.limit_sell_order_id IS NOT NULL THEN 'EXIT_PENDING'
                WHEN NEW.scale_in_order_id IS NOT NULL THEN 'SCALING'
                ELSE 'OPEN'
            END
        );
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_trades_after_update_normalized
    AFTER UPDATE ON trades
    BEGIN
        INSERT OR IGNORE INTO windows (symbol, slug, window_start, window_end, token_id, status, settled, settled_at, created_at)
        SELECT NEW.symbol, NEW.slug, NEW.window_start, NEW.window_end, NEW.token_id,
               CASE WHEN NEW.settled = 1 THEN 'CLOSED' ELSE 'OPEN' END,
               NEW.settled,
               NEW.settled_at,
               COALESCE(NEW.timestamp, datetime('now'))
        WHERE NEW.window_start IS NOT NULL;

        UPDATE windows
        SET window_end = COALESCE(NEW.window_end, window_end),
            slug = COALESCE(NEW.slug, slug),
            token_id = COALESCE(NEW.token_id, token_id),
            status = CASE
                WHEN (
                    SELECT COUNT(1)
                    FROM trades t
                    WHERE t.symbol = NEW.symbol AND t.window_start = NEW.window_start AND t.settled = 0
                ) = 0 AND NEW.settled = 1 THEN 'CLOSED'
                WHEN NEW.settled = 1 THEN 'CLOSED'
                ELSE status
            END,
            settled = CASE
                WHEN (
                    SELECT COUNT(1)
                    FROM trades t
                    WHERE t.symbol = NEW.symbol AND t.window_start = NEW.window_start AND t.settled = 0
                ) = 0 THEN 1
                ELSE settled
            END,
            settled_at = CASE
                WHEN NEW.settled = 1 THEN COALESCE(NEW.settled_at, settled_at)
                ELSE settled_at
            END
        WHERE NEW.window_start IS NOT NULL
          AND symbol = NEW.symbol
          AND window_start = NEW.window_start;

        UPDATE positions
        SET window_id = (CASE WHEN NEW.window_start IS NOT NULL THEN (SELECT id FROM windows WHERE symbol = NEW.symbol AND window_start = NEW.window_start) ELSE window_id END),
            symbol = NEW.symbol,
            side = NEW.side,
            token_id = NEW.token_id,
            entry_price = NEW.entry_price,
            size = NEW.size,
            bet_usd = NEW.bet_usd,
            p_yes = NEW.p_yes,
            best_bid = NEW.best_bid,
            best_ask = NEW.best_ask,
            imbalance = NEW.imbalance,
            funding_bias = NEW.funding_bias,
            order_status = NEW.order_status,
            order_id = NEW.order_id,
            limit_sell_order_id = NEW.limit_sell_order_id,
            scale_in_order_id = NEW.scale_in_order_id,
            target_price = NEW.target_price,
            is_reversal = NEW.is_reversal,
            reversal_triggered = NEW.reversal_triggered,
            reversal_triggered_at = NEW.reversal_triggered_at,
            last_scale_in_at = NEW.last_scale_in_at,
            final_outcome = NEW.final_outcome,
            exit_price = NEW.exit_price,
            pnl_usd = NEW.pnl_usd,
            roi_pct = NEW.roi_pct,
            settled = NEW.settled,
            settled_at = NEW.settled_at,
            exited_early = NEW.exited_early,
            scaled_in = NEW.scaled_in,
            entry_timestamp = NEW.timestamp,
            window_start = NEW.window_start,
            window_end = NEW.window_end,
            status = CASE
                WHEN NEW.settled = 1 THEN 'CLOSED'
                WHEN NEW.limit_sell_order_id IS NOT NULL THEN 'EXIT_PENDING'
                WHEN NEW.scale_in_order_id IS NOT NULL THEN 'SCALING'
                ELSE 'OPEN'
            END
        WHERE trade_id = NEW.id;
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_trades_after_delete_normalized
    AFTER DELETE ON trades
    BEGIN
        DELETE FROM positions WHERE trade_id = OLD.id;
        DELETE FROM orders WHERE trade_id = OLD.id;

        UPDATE windows
        SET settled = CASE
                WHEN (
                    SELECT COUNT(1)
                    FROM trades t
                    WHERE t.symbol = OLD.symbol AND t.window_start = OLD.window_start
                ) = 0 THEN 0
                ELSE settled
            END,
            status = CASE
                WHEN (
                    SELECT COUNT(1)
                    FROM trades t
                    WHERE t.symbol = OLD.symbol AND t.window_start = OLD.window_start
                ) = 0 THEN 'OPEN'
                ELSE status
            END,
            settled_at = CASE
                WHEN (
                    SELECT COUNT(1)
                    FROM trades t
                    WHERE t.symbol = OLD.symbol AND t.window_start = OLD.window_start
                ) = 0 THEN NULL
                ELSE settled_at
            END
        WHERE OLD.window_start IS NOT NULL
          AND symbol = OLD.symbol
          AND window_start = OLD.window_start;
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_orders_entry_after_insert
    AFTER INSERT ON trades
    WHEN NEW.order_id IS NOT NULL AND LENGTH(TRIM(NEW.order_id)) > 0 AND NEW.order_id <> 'N/A'
    BEGIN
        INSERT OR IGNORE INTO orders (
            trade_id, window_id, symbol, order_id, order_role, side, price, size, bet_usd, status, created_at
        )
        VALUES (
            NEW.id,
            (CASE WHEN NEW.window_start IS NOT NULL THEN (SELECT id FROM windows WHERE symbol = NEW.symbol AND window_start = NEW.window_start) ELSE NULL END),
            NEW.symbol,
            NEW.order_id,
            'ENTRY',
            NEW.side,
            NEW.entry_price,
            NEW.size,
            NEW.bet_usd,
            NEW.order_status,
            COALESCE(NEW.timestamp, datetime('now'))
        );
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_orders_entry_status_update
    AFTER UPDATE OF order_status ON trades
    WHEN NEW.order_id IS NOT NULL AND LENGTH(TRIM(NEW.order_id)) > 0 AND NEW.order_id <> 'N/A'
    BEGIN
        UPDATE orders
        SET status = NEW.order_status,
            price = NEW.entry_price,
            size = NEW.size,
            bet_usd = NEW.bet_usd
        WHERE trade_id = NEW.id AND order_role = 'ENTRY';
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_orders_limit_after_update
    AFTER UPDATE ON trades
    WHEN NEW.limit_sell_order_id IS NOT NULL AND LENGTH(TRIM(NEW.limit_sell_order_id)) > 0
         AND (OLD.limit_sell_order_id IS NULL OR OLD.limit_sell_order_id <> NEW.limit_sell_order_id)
    BEGIN
        INSERT OR IGNORE INTO orders (
            trade_id, window_id, symbol, order_id, order_role, side, price, size, bet_usd, status, created_at
        )
        VALUES (
            NEW.id,
            (CASE WHEN NEW.window_start IS NOT NULL THEN (SELECT id FROM windows WHERE symbol = NEW.symbol AND window_start = NEW.window_start) ELSE NULL END),
            NEW.symbol,
            NEW.limit_sell_order_id,
            'EXIT_PLAN',
            NEW.side,
            NEW.target_price,
            NEW.size,
            NEW.bet_usd,
            'OPEN',
            datetime('now')
        );
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_orders_limit_cleared
    AFTER UPDATE ON trades
    WHEN NEW.limit_sell_order_id IS NULL AND OLD.limit_sell_order_id IS NOT NULL AND LENGTH(TRIM(OLD.limit_sell_order_id)) > 0
    BEGIN
        UPDATE orders
        SET status = 'CLEARED'
        WHERE order_id = OLD.limit_sell_order_id;
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_orders_scale_in_after_update
    AFTER UPDATE ON trades
    WHEN NEW.scale_in_order_id IS NOT NULL AND LENGTH(TRIM(NEW.scale_in_order_id)) > 0
         AND (OLD.scale_in_order_id IS NULL OR OLD.scale_in_order_id <> NEW.scale_in_order_id)
    BEGIN
        INSERT OR IGNORE INTO orders (
            trade_id, window_id, symbol, order_id, order_role, side, price, size, bet_usd, status, created_at
        )
        VALUES (
            NEW.id,
            (CASE WHEN NEW.window_start IS NOT NULL THEN (SELECT id FROM windows WHERE symbol = NEW.symbol AND window_start = NEW.window_start) ELSE NULL END),
            NEW.symbol,
            NEW.scale_in_order_id,
            'SCALE_IN',
            NEW.side,
            NEW.entry_price,
            NEW.size,
            NEW.bet_usd,
            'PENDING',
            datetime('now')
        );
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_orders_scale_in_cleared
    AFTER UPDATE ON trades
    WHEN NEW.scale_in_order_id IS NULL AND OLD.scale_in_order_id IS NOT NULL AND LENGTH(TRIM(OLD.scale_in_order_id)) > 0
    BEGIN
        UPDATE orders
        SET status = 'CLEARED'
        WHERE order_id = OLD.scale_in_order_id;
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_window_stats_after_insert
    AFTER INSERT ON trades
    WHEN NEW.window_start IS NOT NULL
    BEGIN
        INSERT INTO window_stats (
            window_id, symbol, window_start, total_trades, open_positions, settled_positions,
            gross_exposure, avg_edge, avg_roi, realized_pnl, unrealized_pnl, last_updated
        )
        SELECT
            w.id,
            w.symbol,
            w.window_start,
            (SELECT COUNT(*) FROM trades WHERE symbol = NEW.symbol AND window_start = NEW.window_start),
            (SELECT COUNT(*) FROM trades WHERE symbol = NEW.symbol AND window_start = NEW.window_start AND settled = 0),
            (SELECT COUNT(*) FROM trades WHERE symbol = NEW.symbol AND window_start = NEW.window_start AND settled = 1),
            COALESCE((SELECT SUM(COALESCE(bet_usd, 0.0)) FROM trades WHERE symbol = NEW.symbol AND window_start = NEW.window_start AND settled = 0), 0.0),
            COALESCE((SELECT AVG(COALESCE(edge, 0.0)) FROM trades WHERE symbol = NEW.symbol AND window_start = NEW.window_start), 0.0),
            COALESCE((SELECT AVG(COALESCE(roi_pct, 0.0)) FROM trades WHERE symbol = NEW.symbol AND window_start = NEW.window_start AND settled = 1), 0.0),
            COALESCE((SELECT SUM(COALESCE(pnl_usd, 0.0)) FROM trades WHERE symbol = NEW.symbol AND window_start = NEW.window_start AND settled = 1), 0.0),
            COALESCE((SELECT SUM(COALESCE(pnl_usd, 0.0)) FROM trades WHERE symbol = NEW.symbol AND window_start = NEW.window_start AND settled = 0), 0.0),
            datetime('now')
        FROM windows w
        WHERE w.symbol = NEW.symbol AND w.window_start = NEW.window_start
        ON CONFLICT(window_id) DO UPDATE SET
            symbol = excluded.symbol,
            window_start = excluded.window_start,
            total_trades = excluded.total_trades,
            open_positions = excluded.open_positions,
            settled_positions = excluded.settled_positions,
            gross_exposure = excluded.gross_exposure,
            avg_edge = excluded.avg_edge,
            avg_roi = excluded.avg_roi,
            realized_pnl = excluded.realized_pnl,
            unrealized_pnl = excluded.unrealized_pnl,
            last_updated = excluded.last_updated;
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_window_stats_after_update
    AFTER UPDATE ON trades
    WHEN NEW.window_start IS NOT NULL
    BEGIN
        INSERT INTO window_stats (
            window_id, symbol, window_start, total_trades, open_positions, settled_positions,
            gross_exposure, avg_edge, avg_roi, realized_pnl, unrealized_pnl, last_updated
        )
        SELECT
            w.id,
            w.symbol,
            w.window_start,
            (SELECT COUNT(*) FROM trades WHERE symbol = NEW.symbol AND window_start = NEW.window_start),
            (SELECT COUNT(*) FROM trades WHERE symbol = NEW.symbol AND window_start = NEW.window_start AND settled = 0),
            (SELECT COUNT(*) FROM trades WHERE symbol = NEW.symbol AND window_start = NEW.window_start AND settled = 1),
            COALESCE((SELECT SUM(COALESCE(bet_usd, 0.0)) FROM trades WHERE symbol = NEW.symbol AND window_start = NEW.window_start AND settled = 0), 0.0),
            COALESCE((SELECT AVG(COALESCE(edge, 0.0)) FROM trades WHERE symbol = NEW.symbol AND window_start = NEW.window_start), 0.0),
            COALESCE((SELECT AVG(COALESCE(roi_pct, 0.0)) FROM trades WHERE symbol = NEW.symbol AND window_start = NEW.window_start AND settled = 1), 0.0),
            COALESCE((SELECT SUM(COALESCE(pnl_usd, 0.0)) FROM trades WHERE symbol = NEW.symbol AND window_start = NEW.window_start AND settled = 1), 0.0),
            COALESCE((SELECT SUM(COALESCE(pnl_usd, 0.0)) FROM trades WHERE symbol = NEW.symbol AND window_start = NEW.window_start AND settled = 0), 0.0),
            datetime('now')
        FROM windows w
        WHERE w.symbol = NEW.symbol AND w.window_start = NEW.window_start
        ON CONFLICT(window_id) DO UPDATE SET
            symbol = excluded.symbol,
            window_start = excluded.window_start,
            total_trades = excluded.total_trades,
            open_positions = excluded.open_positions,
            settled_positions = excluded.settled_positions,
            gross_exposure = excluded.gross_exposure,
            avg_edge = excluded.avg_edge,
            avg_roi = excluded.avg_roi,
            realized_pnl = excluded.realized_pnl,
            unrealized_pnl = excluded.unrealized_pnl,
            last_updated = excluded.last_updated;
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_window_stats_after_delete
    AFTER DELETE ON trades
    WHEN OLD.window_start IS NOT NULL
    BEGIN
        INSERT INTO window_stats (
            window_id, symbol, window_start, total_trades, open_positions, settled_positions,
            gross_exposure, avg_edge, avg_roi, realized_pnl, unrealized_pnl, last_updated
        )
        SELECT
            w.id,
            w.symbol,
            w.window_start,
            (SELECT COUNT(*) FROM trades WHERE symbol = OLD.symbol AND window_start = OLD.window_start),
            (SELECT COUNT(*) FROM trades WHERE symbol = OLD.symbol AND window_start = OLD.window_start AND settled = 0),
            (SELECT COUNT(*) FROM trades WHERE symbol = OLD.symbol AND window_start = OLD.window_start AND settled = 1),
            COALESCE((SELECT SUM(COALESCE(bet_usd, 0.0)) FROM trades WHERE symbol = OLD.symbol AND window_start = OLD.window_start AND settled = 0), 0.0),
            COALESCE((SELECT AVG(COALESCE(edge, 0.0)) FROM trades WHERE symbol = OLD.symbol AND window_start = OLD.window_start), 0.0),
            COALESCE((SELECT AVG(COALESCE(roi_pct, 0.0)) FROM trades WHERE symbol = OLD.symbol AND window_start = OLD.window_start AND settled = 1), 0.0),
            COALESCE((SELECT SUM(COALESCE(pnl_usd, 0.0)) FROM trades WHERE symbol = OLD.symbol AND window_start = OLD.window_start AND settled = 1), 0.0),
            COALESCE((SELECT SUM(COALESCE(pnl_usd, 0.0)) FROM trades WHERE symbol = OLD.symbol AND window_start = OLD.window_start AND settled = 0), 0.0),
            datetime('now')
        FROM windows w
        WHERE w.symbol = OLD.symbol AND w.window_start = OLD.window_start
        ON CONFLICT(window_id) DO UPDATE SET
            symbol = excluded.symbol,
            window_start = excluded.window_start,
            total_trades = excluded.total_trades,
            open_positions = excluded.open_positions,
            settled_positions = excluded.settled_positions,
            gross_exposure = excluded.gross_exposure,
            avg_edge = excluded.avg_edge,
            avg_roi = excluded.avg_roi,
            realized_pnl = excluded.realized_pnl,
            unrealized_pnl = excluded.unrealized_pnl,
            last_updated = excluded.last_updated;
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_orders_history_after_insert
    AFTER INSERT ON orders
    BEGIN
        INSERT INTO orders_history (
            order_id, trade_id, window_id, symbol, event_type, status_from, status_to,
            price, size, bet_usd, created_at
        )
        VALUES (
            NEW.order_id, NEW.trade_id, NEW.window_id, NEW.symbol,
            'CREATED', NULL, NEW.status,
            NEW.price, NEW.size, NEW.bet_usd, datetime('now')
        );
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_orders_history_after_update
    AFTER UPDATE ON orders
    BEGIN
        INSERT INTO orders_history (
            order_id, trade_id, window_id, symbol, event_type, status_from, status_to,
            price, size, bet_usd, created_at
        )
        VALUES (
            NEW.order_id, NEW.trade_id, NEW.window_id, NEW.symbol,
            'UPDATED', OLD.status, NEW.status,
            NEW.price, NEW.size, NEW.bet_usd, datetime('now')
        );
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_orders_history_after_delete
    AFTER DELETE ON orders
    BEGIN
        INSERT INTO orders_history (
            order_id, trade_id, window_id, symbol, event_type, status_from, status_to,
            price, size, bet_usd, created_at
        )
        VALUES (
            OLD.order_id, OLD.trade_id, OLD.window_id, OLD.symbol,
            'DELETED', OLD.status, NULL,
            OLD.price, OLD.size, OLD.bet_usd, datetime('now')
        );
    END;
    """,
)


def _execute_statements(cursor, statements: Iterable[str]) -> None:
    for statement in statements:
        cursor.execute(statement)


def ensure_windows_table(cursor) -> None:
    cursor.execute(WINDOWS_TABLE_SQL)
    _execute_statements(cursor, WINDOWS_INDEXES)


def ensure_positions_table(cursor) -> None:
    cursor.execute(POSITIONS_TABLE_SQL)
    _execute_statements(cursor, POSITIONS_INDEXES)


def ensure_orders_table(cursor) -> None:
    cursor.execute(ORDERS_TABLE_SQL)
    _execute_statements(cursor, ORDERS_INDEXES)


def ensure_window_stats_table(cursor) -> None:
    cursor.execute(WINDOW_STATS_TABLE_SQL)
    _execute_statements(cursor, WINDOW_STATS_INDEXES)


def ensure_balances_table(cursor) -> None:
    cursor.execute(BALANCES_TABLE_SQL)
    _execute_statements(cursor, BALANCES_INDEXES)


def ensure_signals_table(cursor) -> None:
    cursor.execute(SIGNALS_TABLE_SQL)
    _execute_statements(cursor, SIGNALS_INDEXES)


def ensure_orders_history_table(cursor) -> None:
    cursor.execute(ORDERS_HISTORY_TABLE_SQL)
    _execute_statements(cursor, ORDERS_HISTORY_INDEXES)


def ensure_normalized_tables(cursor) -> None:
    ensure_windows_table(cursor)
    ensure_positions_table(cursor)
    ensure_orders_table(cursor)
    ensure_window_stats_table(cursor)
    ensure_balances_table(cursor)
    ensure_signals_table(cursor)
    ensure_orders_history_table(cursor)


def ensure_normalization_triggers(cursor) -> None:
    for statement in TRIGGER_STATEMENTS:
        cursor.execute(statement)


def backfill_windows(cursor) -> None:
    cursor.execute(
        """
        INSERT OR IGNORE INTO windows (symbol, slug, window_start, window_end, token_id, status, settled, settled_at, created_at)
        SELECT DISTINCT t.symbol, t.slug, t.window_start, t.window_end, t.token_id,

               CASE WHEN t.settled = 1 THEN 'CLOSED' ELSE 'OPEN' END,
               t.settled,
               t.settled_at,
               COALESCE(t.timestamp, datetime('now'))
        FROM trades t
        WHERE t.window_start IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM windows w WHERE w.symbol = t.symbol AND w.window_start = t.window_start
          )
        ;
        """
    )


def backfill_positions(cursor) -> None:
    cursor.execute(
        """
        INSERT OR IGNORE INTO positions (
            trade_id, window_id, symbol, side, token_id, entry_price, size, bet_usd,
            p_yes, best_bid, best_ask, imbalance, funding_bias, order_status, order_id,
            limit_sell_order_id, scale_in_order_id, target_price, is_reversal, reversal_triggered,
            reversal_triggered_at, last_scale_in_at, final_outcome, exit_price, pnl_usd, roi_pct,
            settled, settled_at, exited_early, scaled_in, entry_timestamp, window_start, window_end, status
        )
        SELECT
            t.id,
            (CASE WHEN t.window_start IS NOT NULL THEN (SELECT id FROM windows w WHERE w.symbol = t.symbol AND w.window_start = t.window_start) ELSE NULL END),
            t.symbol,
            t.side,
            t.token_id,
            t.entry_price,
            t.size,
            t.bet_usd,
            t.p_yes,
            t.best_bid,
            t.best_ask,
            t.imbalance,
            t.funding_bias,
            t.order_status,
            t.order_id,
            t.limit_sell_order_id,
            t.scale_in_order_id,
            t.target_price,
            t.is_reversal,
            t.reversal_triggered,
            t.reversal_triggered_at,
            t.last_scale_in_at,
            t.final_outcome,
            t.exit_price,
            t.pnl_usd,
            t.roi_pct,
            t.settled,
            t.settled_at,
            t.exited_early,
            t.scaled_in,
            t.timestamp,
            t.window_start,
            t.window_end,
            CASE
                WHEN t.settled = 1 THEN 'CLOSED'
                WHEN t.limit_sell_order_id IS NOT NULL THEN 'EXIT_PENDING'
                WHEN t.scale_in_order_id IS NOT NULL THEN 'SCALING'
                ELSE 'OPEN'
            END
        FROM trades t
        WHERE NOT EXISTS (SELECT 1 FROM positions p WHERE p.trade_id = t.id)
        ;
        """
    )


def backfill_orders(cursor) -> None:
    cursor.execute(
        """
        INSERT OR IGNORE INTO orders (
            trade_id, window_id, symbol, order_id, order_role, side, price, size, bet_usd, status, created_at
        )
        SELECT
            t.id,
            (CASE WHEN t.window_start IS NOT NULL THEN (SELECT id FROM windows w WHERE w.symbol = t.symbol AND w.window_start = t.window_start) ELSE NULL END),
            t.symbol,
            t.order_id,
            'ENTRY',
            t.side,
            t.entry_price,
            t.size,
            t.bet_usd,
            t.order_status,
            COALESCE(t.timestamp, datetime('now'))
        FROM trades t
        WHERE t.order_id IS NOT NULL
          AND LENGTH(TRIM(t.order_id)) > 0
          AND t.order_id <> 'N/A'
          AND NOT EXISTS (
              SELECT 1 FROM orders o WHERE o.order_id = t.order_id
          )
        ;
        """
    )

    cursor.execute(
        """
        INSERT OR IGNORE INTO orders (
            trade_id, window_id, symbol, order_id, order_role, side, price, size, bet_usd, status, created_at
        )
        SELECT
            t.id,
            (CASE WHEN t.window_start IS NOT NULL THEN (SELECT id FROM windows w WHERE w.symbol = t.symbol AND w.window_start = t.window_start) ELSE NULL END),
            t.symbol,
            t.limit_sell_order_id,
            'EXIT_PLAN',
            t.side,
            t.target_price,
            t.size,
            t.bet_usd,
            'OPEN',
            datetime('now')
        FROM trades t
        WHERE t.limit_sell_order_id IS NOT NULL
          AND LENGTH(TRIM(t.limit_sell_order_id)) > 0
          AND NOT EXISTS (
              SELECT 1 FROM orders o WHERE o.order_id = t.limit_sell_order_id
          )
        ;
        """
    )

    cursor.execute(
        """
        INSERT OR IGNORE INTO orders (
            trade_id, window_id, symbol, order_id, order_role, side, price, size, bet_usd, status, created_at
        )
        SELECT
            t.id,
            (CASE WHEN t.window_start IS NOT NULL THEN (SELECT id FROM windows w WHERE w.symbol = t.symbol AND w.window_start = t.window_start) ELSE NULL END),
            t.symbol,
            t.scale_in_order_id,
            'SCALE_IN',
            t.side,
            t.entry_price,
            t.size,
            t.bet_usd,
            'PENDING',
            datetime('now')
        FROM trades t
        WHERE t.scale_in_order_id IS NOT NULL
          AND LENGTH(TRIM(t.scale_in_order_id)) > 0
          AND NOT EXISTS (
              SELECT 1 FROM orders o WHERE o.order_id = t.scale_in_order_id
          )
        ;
        """
    )


def backfill_window_stats(cursor) -> None:
    cursor.execute(
        """
        INSERT OR REPLACE INTO window_stats (
            window_id, symbol, window_start, total_trades, open_positions, settled_positions,
            gross_exposure, avg_edge, avg_roi, realized_pnl, unrealized_pnl, last_updated
        )
        SELECT
            w.id,
            w.symbol,
            w.window_start,
            COALESCE((SELECT COUNT(*) FROM trades t WHERE t.symbol = w.symbol AND t.window_start = w.window_start), 0),
            COALESCE((SELECT COUNT(*) FROM trades t WHERE t.symbol = w.symbol AND t.window_start = w.window_start AND t.settled = 0), 0),
            COALESCE((SELECT COUNT(*) FROM trades t WHERE t.symbol = w.symbol AND t.window_start = w.window_start AND t.settled = 1), 0),
            COALESCE((SELECT SUM(COALESCE(bet_usd, 0.0)) FROM trades t WHERE t.symbol = w.symbol AND t.window_start = w.window_start AND t.settled = 0), 0.0),
            COALESCE((SELECT AVG(COALESCE(edge, 0.0)) FROM trades t WHERE t.symbol = w.symbol AND t.window_start = w.window_start), 0.0),
            COALESCE((SELECT AVG(COALESCE(roi_pct, 0.0)) FROM trades t WHERE t.symbol = w.symbol AND t.window_start = w.window_start AND t.settled = 1), 0.0),
            COALESCE((SELECT SUM(COALESCE(pnl_usd, 0.0)) FROM trades t WHERE t.symbol = w.symbol AND t.window_start = w.window_start AND t.settled = 1), 0.0),
            COALESCE((SELECT SUM(COALESCE(pnl_usd, 0.0)) FROM trades t WHERE t.symbol = w.symbol AND t.window_start = w.window_start AND t.settled = 0), 0.0),
            datetime('now')
        FROM windows w
        ;
        """
    )


def backfill_orders_history(cursor) -> None:
    cursor.execute(
        """
        INSERT OR IGNORE INTO orders_history (
            order_id, trade_id, window_id, symbol, event_type, status_from, status_to,
            price, size, bet_usd, created_at
        )
        SELECT
            o.order_id,
            o.trade_id,
            o.window_id,
            o.symbol,
            'CREATED',
            NULL,
            o.status,
            o.price,
            o.size,
            o.bet_usd,
            datetime('now')
        FROM orders o
        WHERE NOT EXISTS (
            SELECT 1 FROM orders_history h WHERE h.order_id = o.order_id AND h.event_type = 'CREATED'
        )
        ;
        """
    )
