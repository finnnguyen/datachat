"""
Proves that run_query() is read-only at the database layer (PRAGMA query_only = ON),
independent of the keyword blocklist in sql_validator.py.

Every statement below is sent straight to run_query(), skipping validate_sql(),
i.e. as if the blocklist had been bypassed.

Usage:
    python eval/test_readonly.py
"""

import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.sql_executor import run_query
from backend.sql_validator import validate_sql

WRITE_STATEMENTS = {
    "INSERT": "INSERT INTO t (id, name) VALUES (99, 'evil')",
    "UPDATE": "UPDATE t SET name = 'evil'",
    "DELETE": "DELETE FROM t",
    "DROP": "DROP TABLE t",
    "CREATE": "CREATE TABLE evil (x INTEGER)",
}


def _make_db(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE t (id INTEGER, name TEXT)")
    conn.executemany("INSERT INTO t VALUES (?, ?)", [(1, "a"), (2, "b")])
    conn.commit()
    conn.close()


def _row_count(path):
    conn = sqlite3.connect(path)
    n = conn.execute("SELECT COUNT(*) FROM t").fetchone()[0]
    conn.close()
    return n


def main():
    failures = 0

    def check(label, ok, detail=""):
        nonlocal failures
        print(f"  {'PASS' if ok else 'FAIL'}: {label}" + (f"  [{detail}]" if detail else ""))
        if not ok:
            failures += 1

    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        _make_db(db)

        print("Control: a plain connection WITHOUT query_only can write (so the test is meaningful)")
        conn = sqlite3.connect(db)
        conn.execute("INSERT INTO t VALUES (3, 'c')")
        seen = conn.execute("SELECT COUNT(*) FROM t").fetchone()[0]
        conn.rollback()  # leave the fixture untouched
        conn.close()
        check("plain sqlite3 connection accepts INSERT", seen == 3, f"saw {seen} rows mid-transaction")

        print("\nWrites sent directly to run_query(), blocklist bypassed:")
        for name, sql in WRITE_STATEMENTS.items():
            rows, err = run_query(sql, db_path=db)
            check(f"{name} rejected at DB level", bool(err), err)

        print("\nStacked statement trying to switch the pragma off:")
        rows, err = run_query("SELECT 1; PRAGMA query_only = OFF; DROP TABLE t", db_path=db)
        check("stacked statements rejected", bool(err), err)

        print("\nData intact after all attempts:")
        check("table t still has 2 rows", _row_count(db) == 2)
        conn = sqlite3.connect(db)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        check("no extra table 'evil' created", "evil" not in tables)

        print("\nReads still work:")
        rows, err = run_query("SELECT id, name FROM t ORDER BY id", db_path=db)
        check("SELECT returns rows", not err and len(rows) == 2, err or f"{len(rows)} rows")

        print("\nFirst layer (blocklist) still active:")
        for name, sql in WRITE_STATEMENTS.items():
            ok, msg = validate_sql(sql)
            check(f"validate_sql blocks {name}", not ok)

    print()
    if failures:
        print(f"{failures} check(s) FAILED")
        sys.exit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
