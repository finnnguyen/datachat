import sqlite3
from backend.csv_processor import DB_PATH


def run_query(sql: str, db_path: str = DB_PATH) -> tuple[list[dict], str]:
    """
    Execute a SQL query and return (rows, error).
    rows is a list of dicts; error is empty string on success.
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(sql)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows, ""
    except sqlite3.OperationalError as e:
        return [], f"SQL execution error: {e}"
    except Exception as e:
        return [], f"Unexpected error: {e}"
