import os
import sqlite3
import uuid
from datetime import datetime

DB_NAME = "agentbd.db"


def init_db() -> None:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id TEXT PRIMARY KEY,
                    name TEXT,
                    username TEXT,
                    email TEXT,
                    balance REAL DEFAULT 0.0,
                    bonus REAL DEFAULT 0.0,
                    referral_code TEXT UNIQUE,
                    referred_by TEXT,
                    total_orders INTEGER DEFAULT 0,
                    is_admin INTEGER DEFAULT 0,
                    created_at TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    emoji TEXT DEFAULT '🤖',
                    is_active INTEGER DEFAULT 1
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    description TEXT,
                    price REAL,
                    category_id INTEGER,
                    file_url TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    agent_id INTEGER,
                    agent_name TEXT,
                    amount REAL,
                    payment_method TEXT,
                    txn_id TEXT,
                    status TEXT DEFAULT 'pending',
                    delivery_url TEXT,
                    created_at TEXT,
                    delivered_at TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS withdrawals (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    amount REAL,
                    wallet_address TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT,
                    processed_at TEXT
                )
            """)

            default_categories = [
                ("WhatsApp Bots", "🤖"),
                ("Telegram Bots", "💬"),
                ("AI Tools", "🧠"),
                ("Automation", "⚙️"),
            ]
            for cat_name, cat_emoji in default_categories:
                cursor.execute(
                    "INSERT OR IGNORE INTO categories (name, emoji) VALUES (?, ?)",
                    (cat_name, cat_emoji),
                )

            sample_agents = [
                (
                    "WhatsApp Business Bot",
                    "A powerful WhatsApp Business automation bot.",
                    10.0,
                    1,
                    "",
                ),
                (
                    "Telegram UI Bot",
                    "A feature-rich Telegram bot with a beautiful UI.",
                    15.0,
                    1,
                    "",
                ),
            ]
            for agent in sample_agents:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO agents (name, description, price, category_id, file_url, created_at)
                    SELECT ?, ?, ?, ?, ?, ?
                    WHERE NOT EXISTS (SELECT 1 FROM agents WHERE name = ?)
                    """,
                    (
                        agent[0],
                        agent[1],
                        agent[2],
                        agent[3],
                        agent[4],
                        datetime.now().isoformat(),
                        agent[0],
                    ),
                )

            conn.commit()
            print("✅ Database initialized")
    except Exception as e:
        print(f"❌ init_db error: {e}")


def get_or_create_user(
    telegram_id: str,
    name: str,
    username: str,
    referred_by: str = None,
) -> dict:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            )
            row = cursor.fetchone()

            if row:
                return dict(row)

            referral_code = str(uuid.uuid4()).replace("-", "")[:8]

            signup_bonus = float(os.environ.get("SIGNUP_BONUS_AMOUNT", "1.0"))

            valid_referrer = None
            if referred_by:
                cursor.execute(
                    "SELECT telegram_id FROM users WHERE referral_code = ?",
                    (referred_by,),
                )
                referrer_row = cursor.fetchone()
                if referrer_row:
                    valid_referrer = referrer_row["telegram_id"]

            cursor.execute(
                """
                INSERT INTO users (
                    telegram_id, name, username, email, balance, bonus,
                    referral_code, referred_by, total_orders, is_admin, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    telegram_id,
                    name,
                    username,
                    None,
                    signup_bonus,
                    0.0,
                    referral_code,
                    valid_referrer,
                    0,
                    0,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

            if valid_referrer:
                add_referral_bonus(valid_referrer, signup_bonus)

            cursor.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            )
            new_row = cursor.fetchone()
            print(f"✅ New user: {name}")
            return dict(new_row)
    except Exception as e:
        print(f"❌ get_or_create_user error: {e}")
        return {}


def get_user(telegram_id: str) -> dict | None:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    except Exception as e:
        print(f"❌ get_user error: {e}")
        return None


def update_user_balance(telegram_id: str, amount: float) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET balance = balance + ? WHERE telegram_id = ?",
                (amount, telegram_id),
            )
            conn.commit()
            print(f"✅ Balance updated for {telegram_id}: +{amount}")
            return True
    except Exception as e:
        print(f"❌ update_user_balance error: {e}")
        return False


def deduct_user_balance(telegram_id: str, amount: float) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,)
            )
            row = cursor.fetchone()
            if not row:
                print(f"❌ deduct_user_balance: user {telegram_id} not found")
                return False
            current_balance = row["balance"]
            if current_balance < amount:
                print(
                    f"❌ deduct_user_balance: insufficient balance for {telegram_id}"
                )
                return False
            cursor.execute(
                "UPDATE users SET balance = balance - ? WHERE telegram_id = ?",
                (amount, telegram_id),
            )
            conn.commit()
            print(f"✅ Balance deducted for {telegram_id}: -{amount}")
            return True
    except Exception as e:
        print(f"❌ deduct_user_balance error: {e}")
        return False


def update_user_email(telegram_id: str, email: str) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET email = ? WHERE telegram_id = ?",
                (email, telegram_id),
            )
            conn.commit()
            print(f"✅ Email updated for {telegram_id}")
            return True
    except Exception as e:
        print(f"❌ update_user_email error: {e}")
        return False


def get_all_categories() -> list:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM categories WHERE is_active = 1 ORDER BY id ASC"
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ get_all_categories error: {e}")
        return []


def get_agents_by_category(category_id: int) -> list:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM agents WHERE category_id = ? AND is_active = 1 ORDER BY id ASC",
                (category_id,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ get_agents_by_category error: {e}")
        return []


def get_all_agents() -> list:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM agents WHERE is_active = 1 ORDER BY id ASC"
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ get_all_agents error: {e}")
        return []


def get_agent(agent_id: int) -> dict | None:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM agents WHERE id = ? AND is_active = 1",
                (agent_id,),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    except Exception as e:
        print(f"❌ get_agent error: {e}")
        return None


def create_order(
    order_id: str,
    user_id: str,
    agent_id: int,
    agent_name: str,
    amount: float,
    payment_method: str,
    txn_id: str,
) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO orders (
                    id, user_id, agent_id, agent_name, amount,
                    payment_method, txn_id, status, delivery_url, created_at, delivered_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    user_id,
                    agent_id,
                    agent_name,
                    amount,
                    payment_method,
                    txn_id,
                    "pending",
                    None,
                    datetime.now().isoformat(),
                    None,
                ),
            )
            cursor.execute(
                "UPDATE users SET total_orders = total_orders + 1 WHERE telegram_id = ?",
                (user_id,),
            )
            conn.commit()
            print(f"✅ Order created: {order_id} for user {user_id}")
            return True
    except Exception as e:
        print(f"❌ create_order error: {e}")
        return False


def get_order(order_id: str) -> dict | None:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM orders WHERE id = ?", (order_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    except Exception as e:
        print(f"❌ get_order error: {e}")
        return None


def get_user_orders(user_id: str) -> list:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ get_user_orders error: {e}")
        return []


def update_order_status(
    order_id: str, status: str, delivery_url: str = None
) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            if status == "delivered":
                cursor.execute(
                    """
                    UPDATE orders
                    SET status = ?, delivered_at = ?, delivery_url = ?
                    WHERE id = ?
                    """,
                    (
                        status,
                        datetime.now().isoformat(),
                        delivery_url,
                        order_id,
                    ),
                )
            else:
                cursor.execute(
                    "UPDATE orders SET status = ? WHERE id = ?",
                    (status, order_id),
                )
            conn.commit()
            print(f"✅ Order {order_id} status updated to {status}")
            return True
    except Exception as e:
        print(f"❌ update_order_status error: {e}")
        return False


def create_withdrawal(
    withdrawal_id: str,
    user_id: str,
    amount: float,
    wallet_address: str,
) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO withdrawals (
                    id, user_id, amount, wallet_address, status, created_at, processed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    withdrawal_id,
                    user_id,
                    amount,
                    wallet_address,
                    "pending",
                    datetime.now().isoformat(),
                    None,
                ),
            )
            conn.commit()
            print(f"✅ Withdrawal created: {withdrawal_id} for user {user_id}")
            return True
    except Exception as e:
        print(f"❌ create_withdrawal error: {e}")
        return False


def get_pending_withdrawals() -> list:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM withdrawals WHERE status = 'pending' ORDER BY created_at ASC"
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ get_pending_withdrawals error: {e}")
        return []


def update_withdrawal_status(withdrawal_id: str, status: str) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE withdrawals
                SET status = ?, processed_at = ?
                WHERE id = ?
                """,
                (status, datetime.now().isoformat(), withdrawal_id),
            )
            conn.commit()
            print(f"✅ Withdrawal {withdrawal_id} status updated to {status}")
            return True
    except Exception as e:
        print(f"❌ update_withdrawal_status error: {e}")
        return False


def add_category(name: str, emoji: str) -> int | None:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO categories (name, emoji, is_active) VALUES (?, ?, ?)",
                (name, emoji, 1),
            )
            conn.commit()
            cat_id = cursor.lastrowid
            print(f"✅ Category added: {name} (id={cat_id})")
            return cat_id
    except Exception as e:
        print(f"❌ add_category error: {e}")
        return None


def add_agent(
    name: str,
    description: str,
    price: float,
    category_id: int,
    file_url: str,
) -> int | None:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO agents (name, description, price, category_id, file_url, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    description,
                    price,
                    category_id,
                    file_url,
                    1,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            agent_id = cursor.lastrowid
            print(f"✅ Agent added: {name} (id={agent_id})")
            return agent_id
    except Exception as e:
        print(f"❌ add_agent error: {e}")
        return None


def delete_agent(agent_id: int) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE agents SET is_active = 0 WHERE id = ?",
                (agent_id,),
            )
            conn.commit()
            print(f"✅ Agent {agent_id} marked as inactive (soft delete)")
            return True
    except Exception as e:
        print(f"❌ delete_agent error: {e}")
        return False


def get_all_user_ids() -> list:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT telegram_id FROM users")
            rows = cursor.fetchall()
            return [row[0] for row in rows]
    except Exception as e:
        print(f"❌ get_all_user_ids error: {e}")
        return []


def get_stats() -> dict:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM orders")
            total_orders = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COALESCE(SUM(amount), 0.0) FROM orders WHERE status = 'delivered'"
            )
            total_revenue = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM orders WHERE status = 'pending'"
            )
            pending_orders = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COALESCE(SUM(amount), 0.0) FROM withdrawals WHERE status = 'approved'"
            )
            total_withdrawals = cursor.fetchone()[0]

            stats = {
                "total_users": total_users,
                "total_orders": total_orders,
                "total_revenue": total_revenue,
                "pending_orders": pending_orders,
                "total_withdrawals": total_withdrawals,
            }
            print(f"✅ Stats fetched: {stats}")
            return stats
    except Exception as e:
        print(f"❌ get_stats error: {e}")
        return {
            "total_users": 0,
            "total_orders": 0,
            "total_revenue": 0.0,
            "pending_orders": 0,
            "total_withdrawals": 0.0,
        }


def add_referral_bonus(referrer_id: str, bonus_amount: float) -> bool:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE users
                SET bonus = bonus + ?, balance = balance + ?
                WHERE telegram_id = ?
                """,
                (bonus_amount, bonus_amount, referrer_id),
            )
            conn.commit()
            print(
                f"✅ Referral bonus of {bonus_amount} added to {referrer_id}"
            )
            return True
    except Exception as e:
        print(f"❌ add_referral_bonus error: {e}")
        return False
