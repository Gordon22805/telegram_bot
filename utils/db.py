import sqlite3
from datetime import datetime, timezone

DB_PATH = "data.db"


def _connect():
    return sqlite3.connect(DB_PATH)


def init_db():
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS balances (
                user_id INTEGER PRIMARY KEY,
                balance REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                region TEXT NOT NULL,
                qty INTEGER NOT NULL,
                total REAL NOT NULL,
                method TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS topups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                method TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def _utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def create_order(user_id: int, region: str, qty: int, total: float, method: str, status: str) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO orders (user_id, region, qty, total, method, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, region, qty, total, method, status, _utc_now()),
        )
        return int(cur.lastrowid)


def update_order_status(order_id: int, status: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (status, order_id),
        )


def get_balance(user_id: int) -> float:
    with _connect() as conn:
        row = conn.execute(
            "SELECT balance FROM balances WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return float(row[0]) if row else 0.0


def add_balance(user_id: int, amount: float) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO balances (user_id, balance)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET balance = balance + excluded.balance
            """,
            (user_id, amount),
        )


def deduct_balance(user_id: int, amount: float) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT balance FROM balances WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        balance = float(row[0]) if row else 0.0
        if balance < amount:
            return False
        conn.execute(
            "UPDATE balances SET balance = balance - ? WHERE user_id = ?",
            (amount, user_id),
        )
        return True


def get_latest_pending_order(user_id: int):
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT id, region, qty, total, method, status, created_at
            FROM orders
            WHERE user_id = ? AND status = 'pending'
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,),
        )
        return cur.fetchone()


def get_user_stats(user_id: int):
    with _connect() as conn:
        orders = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(total), 0) FROM orders WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        topups = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM topups WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        balance_row = conn.execute(
            "SELECT balance FROM balances WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return {
            "orders_count": orders[0],
            "orders_total": orders[1],
            "topups_count": topups[0],
            "topups_total": topups[1],
            "balance": float(balance_row[0]) if balance_row else 0.0,
        }


def create_topup(user_id: int, amount: float, method: str, status: str) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO topups (user_id, amount, method, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, amount, method, status, _utc_now()),
        )
        return int(cur.lastrowid)


def update_topup_status(topup_id: int, status: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE topups SET status = ? WHERE id = ?",
            (status, topup_id),
        )


def get_topup(topup_id: int):
    with _connect() as conn:
        return conn.execute(
            """
            SELECT id, user_id, amount, method, status, created_at
            FROM topups
            WHERE id = ?
            """,
            (topup_id,),
        ).fetchone()


def get_user_orders(user_id: int, limit: int = 10):
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT id, region, qty, total, method, status, created_at
            FROM orders
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        return cur.fetchall()


def get_user_topups(user_id: int, limit: int = 10):
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT id, amount, method, status, created_at
            FROM topups
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        return cur.fetchall()
