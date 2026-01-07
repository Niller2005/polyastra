import sqlite3

conn = sqlite3.connect("trades.db")
c = conn.cursor()


def table_exists(name: str) -> bool:
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (name,))
    return c.fetchone() is not None


print(f"Total trades: {c.execute('SELECT COUNT(*) FROM trades').fetchone()[0]}")
if table_exists("windows"):
    print(f"Total windows: {c.execute('SELECT COUNT(*) FROM windows').fetchone()[0]}")
if table_exists("positions"):
    print(
        f"Total positions: {c.execute('SELECT COUNT(*) FROM positions').fetchone()[0]}"
    )
if table_exists("orders"):
    print(f"Total orders: {c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]}")
if table_exists("window_stats"):
    print(
        f"Total window_stats rows: {c.execute('SELECT COUNT(*) FROM window_stats').fetchone()[0]}"
    )
if table_exists("balances"):
    print(
        f"Total balances snapshots: {c.execute('SELECT COUNT(*) FROM balances').fetchone()[0]}"
    )
if table_exists("signals"):
    print(
        f"Total signals captured: {c.execute('SELECT COUNT(*) FROM signals').fetchone()[0]}"
    )
if table_exists("orders_history"):
    print(
        f"Total order history events: {c.execute('SELECT COUNT(*) FROM orders_history').fetchone()[0]}"
    )

print("\nRecent 5 trades:")
for row in c.execute(
    "SELECT id, timestamp, symbol, settled FROM trades ORDER BY id DESC LIMIT 5"
).fetchall():
    print(row)

# Check if WAL mode is active and if there are uncommitted changes
print("\n=== Journal Mode ===")
print(c.execute("PRAGMA journal_mode").fetchone())

# Check if there's a WAL file
import os

if os.path.exists("trades.db-wal"):
    print(
        f"\nWAL file exists: trades.db-wal (size: {os.path.getsize('trades.db-wal')} bytes)"
    )
else:
    print("\nNo WAL file found")

if os.path.exists("trades.db-shm"):
    print(
        f"SHM file exists: trades.db-shm (size: {os.path.getsize('trades.db-shm')} bytes)"
    )
else:
    print("No SHM file found")

conn.close()
