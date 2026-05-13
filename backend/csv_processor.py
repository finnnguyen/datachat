import sqlite3
import re
import pandas as pd


DB_PATH = "data/uploads/session.db"


def _sanitize_name(name: str) -> str:
    """Strip non-alphanumeric chars and truncate to 50 chars to prevent prompt injection."""
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", str(name))
    return clean[:50].strip("_") or "col"


def load_csv(file_path: str, original_name: str = None) -> dict:
    """
    Read a CSV into a SQLite table and return its schema.
    original_name: the user-facing filename (e.g. 'sales.csv'); used for the table name.
    Returns: { table_name, db_path, columns: [{name, type}] }
    """
    df = pd.read_csv(file_path)

    # Sanitize column names before they touch any prompt or SQL
    df.columns = [_sanitize_name(c) for c in df.columns]

    name_source = original_name or file_path.split("/")[-1]
    table_name = _sanitize_name(
        name_source.rsplit(".", 1)[0]  # strip extension
    )

    conn = sqlite3.connect(DB_PATH)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()

    schema = _get_schema(table_name)
    return {"table_name": table_name, "db_path": DB_PATH, "columns": schema}


def _get_schema(table_name: str) -> list[dict]:
    """Return [{name, type}] for each column in the table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    rows = cursor.fetchall()
    conn.close()
    return [{"name": row[1], "type": row[2]} for row in rows]


def get_schema(table_name: str) -> list[dict]:
    return _get_schema(table_name)


def build_schema_block(columns: list[dict]) -> str:
    """Format columns as a prompt-ready string."""
    lines = []
    for col in columns:
        lines.append(f"  - {col['name']} ({col['type']})")
    return "\n".join(lines)
