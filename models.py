import os
import shutil
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# On Vercel / serverless platforms, the file system is read-only except /tmp
if os.environ.get("VERCEL") or not os.access(BASE_DIR, os.W_OK):
    DB_PATH = "/tmp/finance.db"
    repo_db = os.path.join(BASE_DIR, "database", "finance.db")
    if os.path.exists(repo_db) and not os.path.exists(DB_PATH):
        try:
            shutil.copyfile(repo_db, DB_PATH)
        except Exception:
            pass
else:
    DB_PATH = os.path.join(BASE_DIR, "database", "finance.db")


def get_db_connection():
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    except OSError:
        pass
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            category TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0),
            description TEXT,
            date TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            monthly_budget REAL NOT NULL DEFAULT 0,
            month TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, month),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS savings_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            goal_name TEXT NOT NULL,
            target_amount REAL NOT NULL CHECK(target_amount > 0),
            saved_amount REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    conn.commit()
    conn.close()


def register_user(name, email, password_hash):
    conn = get_db_connection()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name.strip(), email.strip().lower(), password_hash),
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id


def get_user_by_email(email):
    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
    ).fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user


def add_transaction(user_id, transaction_type, category, amount, description, date_text):
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO transactions (user_id, type, category, amount, description, date)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            transaction_type.lower(),
            category.strip(),
            float(amount),
            description.strip() if description else "",
            date_text,
        ),
    )
    conn.commit()
    conn.close()


def get_transaction_by_id(user_id, transaction_id):
    conn = get_db_connection()
    txn = conn.execute(
        "SELECT * FROM transactions WHERE id = ? AND user_id = ?",
        (transaction_id, user_id),
    ).fetchone()
    conn.close()
    return txn


def update_transaction(user_id, transaction_id, transaction_type, category, amount, description, date_text):
    conn = get_db_connection()
    conn.execute(
        """
        UPDATE transactions
        SET type = ?, category = ?, amount = ?, description = ?, date = ?
        WHERE id = ? AND user_id = ?
        """,
        (
            transaction_type.lower(),
            category.strip(),
            float(amount),
            description.strip() if description else "",
            date_text,
            transaction_id,
            user_id,
        ),
    )
    conn.commit()
    conn.close()


def delete_transaction(user_id, transaction_id):
    conn = get_db_connection()
    conn.execute(
        "DELETE FROM transactions WHERE id = ? AND user_id = ?",
        (transaction_id, user_id),
    )
    conn.commit()
    conn.close()


def get_transactions(user_id, filters=None):
    conn = get_db_connection()
    query = "SELECT * FROM transactions WHERE user_id = ?"
    params = [user_id]

    query_filters = filters or {}

    if query_filters.get("date_from"):
        query += " AND date >= ?"
        params.append(query_filters["date_from"])
    if query_filters.get("date_to"):
        query += " AND date <= ?"
        params.append(query_filters["date_to"])
    if query_filters.get("category"):
        query += " AND category LIKE ?"
        params.append(f"%{query_filters['category']}%")
    if query_filters.get("type"):
        query += " AND type = ?"
        params.append(query_filters["type"])
    amount_min = query_filters.get("amount_min")
    amount_max = query_filters.get("amount_max")

    if amount_min not in (None, ""):
        query += " AND amount >= ?"
        params.append(float(amount_min))
    if amount_max not in (None, ""):
        query += " AND amount <= ?"
        params.append(float(amount_max))

    sort_by = query_filters.get("sort")
    if sort_by == "amount_high":
        query += " ORDER BY amount DESC, date DESC"
    elif sort_by == "amount_low":
        query += " ORDER BY amount ASC, date DESC"
    elif sort_by == "date_old":
        query += " ORDER BY date ASC, id DESC"
    else:
        query += " ORDER BY date DESC, id DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def get_dashboard_summary(user_id):
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT 
            COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) AS total_income,
            COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS total_expense,
            COUNT(*) AS total_transactions,
            COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) - COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS balance
        FROM transactions
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()

    current_month = datetime.now().strftime("%Y-%m")
    monthly_expense = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions WHERE user_id = ? AND type = 'expense' AND substr(date, 1, 7) = ?",
        (user_id, current_month),
    ).fetchone()

    recent = conn.execute(
        "SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT 5",
        (user_id,),
    ).fetchall()
    conn.close()

    return {
        "total_income": float(row["total_income"]),
        "total_expense": float(row["total_expense"]),
        "balance": float(row["balance"]),
        "total_transactions": row["total_transactions"],
        "monthly_savings": float(row["total_income"]) - float(row["total_expense"]),
        "current_month_expense": float(monthly_expense["total"]),
        "recent_transactions": recent,
    }


def save_budget(user_id, monthly_budget, month=None):
    month_value = month or datetime.now().strftime("%Y-%m")
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO budgets (user_id, monthly_budget, month)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, month)
        DO UPDATE SET monthly_budget = excluded.monthly_budget, created_at = CURRENT_TIMESTAMP
        """,
        (user_id, float(monthly_budget), month_value),
    )
    conn.commit()
    conn.close()


def get_budget(user_id, month=None):
    month_value = month or datetime.now().strftime("%Y-%m")
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM budgets WHERE user_id = ? AND month = ? ORDER BY created_at DESC LIMIT 1",
        (user_id, month_value),
    ).fetchone()
    conn.close()
    return row


def get_budget_usage(user_id, month=None):
    month_value = month or datetime.now().strftime("%Y-%m")
    budget = get_budget(user_id, month_value)
    total_expense = get_monthly_expense_total(user_id, month_value)

    monthly_budget = float(budget["monthly_budget"]) if budget else 0.0
    spent = float(total_expense)
    remaining = monthly_budget - spent
    percent_used = 0 if monthly_budget == 0 else min((spent / monthly_budget) * 100, 100)
    if spent > monthly_budget and monthly_budget > 0:
        percent_used = 100

    return {
        "budget": monthly_budget,
        "spent": spent,
        "remaining": remaining,
        "percent_used": percent_used,
    }


def get_monthly_expense_total(user_id, month=None):
    month_value = month or datetime.now().strftime("%Y-%m")
    conn = get_db_connection()
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions WHERE user_id = ? AND type = 'expense' AND substr(date, 1, 7) = ?",
        (user_id, month_value),
    ).fetchone()
    conn.close()
    return float(row["total"])


def create_goal(user_id, goal_name, target_amount, saved_amount=0):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO savings_goals (user_id, goal_name, target_amount, saved_amount) VALUES (?, ?, ?, ?)",
        (user_id, goal_name.strip(), float(target_amount), float(saved_amount)),
    )
    conn.commit()
    conn.close()


def get_goals(user_id):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM savings_goals WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


def update_goal(user_id, goal_id, goal_name, target_amount, saved_amount):
    conn = get_db_connection()
    conn.execute(
        """
        UPDATE savings_goals
        SET goal_name = ?, target_amount = ?, saved_amount = ?
        WHERE id = ? AND user_id = ?
        """,
        (goal_name.strip(), float(target_amount), float(saved_amount), goal_id, user_id),
    )
    conn.commit()
    conn.close()


def delete_goal(user_id, goal_id):
    conn = get_db_connection()
    conn.execute(
        "DELETE FROM savings_goals WHERE id = ? AND user_id = ?",
        (goal_id, user_id),
    )
    conn.commit()
    conn.close()


def get_expense_by_category(user_id):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT category, SUM(amount) AS total FROM transactions WHERE user_id = ? AND type = 'expense' GROUP BY category ORDER BY total DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


def get_income_vs_expense(user_id):
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN type='income' THEN amount ELSE 0 END), 0) AS income,
            COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END), 0) AS expense
        FROM transactions
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()
    conn.close()
    return {"income": float(row["income"]), "expense": float(row["expense"])}


def get_monthly_expense_trend(user_id, months=6):
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT substr(date, 1, 7) AS month, COALESCE(SUM(amount), 0) AS total
        FROM transactions
        WHERE user_id = ? AND type = 'expense'
        GROUP BY substr(date, 1, 7)
        ORDER BY month DESC
        LIMIT ?
        """,
        (user_id, months),
    ).fetchall()
    conn.close()
    ordered = list(rows)
    ordered.reverse()
    return ordered


def get_monthly_report(user_id, month=None):
    month_value = month or datetime.now().strftime("%Y-%m")
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT category, SUM(amount) AS total FROM transactions WHERE user_id = ? AND type = 'expense' AND substr(date,1,7) = ? GROUP BY category ORDER BY total DESC",
        (user_id, month_value),
    ).fetchall()
    conn.close()
    return rows


def get_category_report(user_id):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT category, SUM(amount) AS total, COUNT(*) as count FROM transactions WHERE user_id = ? GROUP BY category ORDER BY total DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


def get_financial_insights(user_id):
    recent = get_transactions(user_id)
    if not recent:
        return ["Add your first transaction to start receiving financial insights."]

    current_month = datetime.now().strftime("%Y-%m")
    previous_month = (datetime.now().replace(day=1).month - 1) or 12
    previous_year = datetime.now().year if previous_month != 12 else datetime.now().year - 1
    prev_month_value = f"{previous_year}-{previous_month:02d}"

    conn = get_db_connection()
    current_total = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = ? AND type='expense' AND substr(date,1,7)=?",
        (user_id, current_month),
    ).fetchone()
    previous_total = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = ? AND type='expense' AND substr(date,1,7)=?",
        (user_id, prev_month_value),
    ).fetchone()

    current_income = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = ? AND type='income' AND substr(date,1,7)=?",
        (user_id, current_month),
    ).fetchone()
    previous_income = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = ? AND type='income' AND substr(date,1,7)=?",
        (user_id, prev_month_value),
    ).fetchone()
    conn.close()

    insights = []
    current_expense = float(current_total["total"])
    previous_expense = float(previous_total["total"])
    if current_expense > previous_expense:
        insights.append(f"Your expenses are higher than last month by ${current_expense - previous_expense:.2f}.")
    else:
        insights.append(f"You controlled spending well and spent ${current_expense:.2f} this month, which is below last month.")

    category_rows = get_expense_by_category(user_id)
    if category_rows:
        top_category = category_rows[0]
        total_all_expenses = sum(float(row["total"]) for row in category_rows)
        percent = (float(top_category["total"]) / total_all_expenses * 100) if total_all_expenses else 0
        insights.append(f"{top_category['category']} accounts for {percent:.0f}% of your total expenses.")

    if float(current_income["total"]) > float(previous_income["total"]):
        insights.append("Your income has increased compared with last month, which improves your savings potential.")
    else:
        insights.append("Consider reviewing recurring costs to increase monthly savings.")

    budget_usage = get_budget_usage(user_id)
    if budget_usage["budget"] and budget_usage["spent"] > budget_usage["budget"]:
        insights.append("Your budget has exceeded the planned limit. Consider reducing discretionary spending.")

    return insights
