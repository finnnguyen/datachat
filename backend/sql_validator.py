BLOCKED_KEYWORDS = [
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER",
    "CREATE", "TRUNCATE", "EXEC", "EXECUTE", "--", "/*",
]


def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Check that the SQL is a safe SELECT query.
    Returns (is_valid, error_message).
    """
    sql = sql.strip()

    if sql.upper() == "INVALID_QUESTION":
        return False, "That question cannot be answered from this dataset. Try asking about the columns shown in the schema."

    if not sql.upper().startswith("SELECT"):
        return False, "Only SELECT queries are allowed."

    upper = sql.upper()
    for kw in BLOCKED_KEYWORDS:
        if kw in upper:
            return False, f"Query contains a forbidden keyword: '{kw}'. Only read-only SELECT queries are permitted."

    return True, ""
