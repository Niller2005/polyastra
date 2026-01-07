"""Database migrations system"""

from typing import List, Callable, Any
from src.utils.logger import log, log_error
from src.data.db_connection import db_connection
from src.data.schema import (
    backfill_orders,
    backfill_orders_history,
    backfill_positions,
    backfill_window_stats,
    backfill_windows,
    ensure_normalized_tables,
    ensure_normalization_triggers,
)


def get_schema_version(conn: Any) -> int:
    """Get current schema version from database"""
    c = conn.cursor()

    # Create schema_version table if it doesn't exist
    c.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
    """)

    c.execute("SELECT MAX(version) FROM schema_version")
    result = c.fetchone()
    current_version = result[0] if result[0] is not None else 0

    return current_version


def set_schema_version(conn: Any, version: int) -> None:
    """Set schema version in database"""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    c = conn.cursor()
    c.execute(
        "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
        (version, datetime.now(tz=ZoneInfo("UTC")).isoformat()),
    )


def migration_001_add_scale_in_order_id(conn: Any) -> None:
    """Add scale_in_order_id column to track pending scale-in orders"""
    c = conn.cursor()

    # Check if column already exists
    c.execute("PRAGMA table_info(trades)")
    columns = [row[1] for row in c.fetchall()]

    if "scale_in_order_id" not in columns:
        log("  - Adding scale_in_order_id column...")
        c.execute("ALTER TABLE trades ADD COLUMN scale_in_order_id TEXT")
        log("    ✓ Column added")
    else:
        log("    ✓ scale_in_order_id column already exists")


def migration_002_add_created_at_column(conn: Any) -> None:
    """Add created_at as alias for timestamp for better clarity"""
    c = conn.cursor()

    # Note: SQLite doesn't support renaming columns easily
    # We'll just ensure timestamp exists and document it should be used
    c.execute("PRAGMA table_info(trades)")
    columns = [row[1] for row in c.fetchall()]

    if "timestamp" in columns:
        log("    ✓ timestamp column exists (serves as created_at)")
    else:
        log("    ⚠️  timestamp column missing - schema needs rebuild")


def migration_003_add_reversal_triggered_column(conn: Any) -> None:
    """Add reversal_triggered column to track if a reversal has been initiated for a trade"""
    c = conn.cursor()

    c.execute("PRAGMA table_info(trades)")
    columns = [row[1] for row in c.fetchall()]

    if "reversal_triggered" not in columns:
        log("  - Adding reversal_triggered column...")
        c.execute("ALTER TABLE trades ADD COLUMN reversal_triggered BOOLEAN DEFAULT 0")
        log("    ✓ Column added")
    else:
        log("    ✓ reversal_triggered column already exists")


def migration_004_add_reversal_triggered_at_column(conn: Any) -> None:
    """Add reversal_triggered_at column to track when a reversal was initiated"""
    c = conn.cursor()

    c.execute("PRAGMA table_info(trades)")
    columns = [row[1] for row in c.fetchall()]

    if "reversal_triggered_at" not in columns:
        log("  - Adding reversal_triggered_at column...")
        c.execute("ALTER TABLE trades ADD COLUMN reversal_triggered_at TEXT")
        log("    ✓ Column added")
    else:
        log("    ✓ reversal_triggered_at column already exists")


def migration_005_add_last_scale_in_at_column(conn: Any) -> None:
    """Add last_scale_in_at column to track when the last scale-in occurred"""
    c = conn.cursor()

    c.execute("PRAGMA table_info(trades)")
    columns = [row[1] for row in c.fetchall()]

    if "last_scale_in_at" not in columns:
        log("  - Adding last_scale_in_at column...")
        c.execute("ALTER TABLE trades ADD COLUMN last_scale_in_at TEXT")
        log("    ✓ Column added")
    else:
        log("    ✓ last_scale_in_at column already exists")


def migration_006_create_normalized_tables(conn: Any) -> None:
    """Create windows/positions/orders tables and keep them synchronized"""
    c = conn.cursor()

    log("  - Ensuring normalized tables exist")
    ensure_normalized_tables(c)
    log("  - Ensuring normalization triggers exist")
    ensure_normalization_triggers(c)

    log("  - Backfilling windows table")
    backfill_windows(c)
    log("  - Backfilling positions table")
    backfill_positions(c)
    log("  - Backfilling orders table")
    backfill_orders(c)
    log("  - Backfilling window stats table")
    backfill_window_stats(c)
    log("  - Backfilling orders history table")
    backfill_orders_history(c)


# Migration registry: version -> migration function
MIGRATIONS: List[tuple[int, str, Callable]] = [
    (1, "Add scale_in_order_id column", migration_001_add_scale_in_order_id),
    (2, "Verify timestamp column", migration_002_add_created_at_column),
    (3, "Add reversal_triggered column", migration_003_add_reversal_triggered_column),
    (
        4,
        "Add reversal_triggered_at column",
        migration_004_add_reversal_triggered_at_column,
    ),
    (
        5,
        "Add last_scale_in_at column",
        migration_005_add_last_scale_in_at_column,
    ),
    (
        6,
        "Create normalized windows/positions/orders tables",
        migration_006_create_normalized_tables,
    ),
]


def run_migrations() -> None:
    """Run all pending database migrations"""
    with db_connection() as conn:
        try:
            current_version = get_schema_version(conn)
            log(f"📊 Database schema version: {current_version}")

            # Find pending migrations
            pending = [m for m in MIGRATIONS if m[0] > current_version]

            if not pending:
                log("✓ Database schema is up to date")
                return

            log(f"🔄 Running {len(pending)} pending migrations...")

            latest_version = current_version
            for version, description, migration_func in pending:
                log(f"  Migration {version}: {description}")
                try:
                    migration_func(conn)
                    set_schema_version(conn, version)
                    latest_version = version
                    log(f"    ✓ Migration {version} completed")
                except Exception as e:
                    log_error(f"Migration {version} failed: {e}")
                    conn.rollback()
                    raise

            log(f"✓ All migrations completed. Schema version: {latest_version}")

        except Exception as e:
            log_error(f"Migration error: {e}")
            raise


def add_migration(description: str, migration_func: Callable) -> None:
    """
    Helper to add a new migration (for future use)

    Usage:
        def migration_003_add_my_column(conn):
            c = conn.cursor()
            c.execute("ALTER TABLE trades ADD COLUMN my_column TEXT")

        # Add to MIGRATIONS list manually
    """
    next_version = max([m[0] for m in MIGRATIONS]) + 1 if MIGRATIONS else 1
    MIGRATIONS.append((next_version, description, migration_func))
    log(f"Migration {next_version} registered: {description}")
