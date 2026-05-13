"""
Evaluation script for DataChat text-to-SQL pipeline.
Uses data/samples/sales.csv as the fixed test dataset.

Usage:
    python eval/eval.py                    # current prompt (V2 few-shot)
    python eval/eval.py --prompt-version 1 # simple prompt, no few-shot (V1 baseline)
    python eval/eval.py --prompt-version 2 # full prompt with few-shot examples (V2)

Prints per-case pass/fail and an overall accuracy score.
Requires OPENAI_API_KEY to be set in .env
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from backend.csv_processor import load_csv
from backend.sql_validator import validate_sql
from backend.sql_executor import run_query
from backend.explainer import explain_result
import backend.sql_generator as _gen

SAMPLE_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "samples", "sales.csv")
TEST_CASES_PATH = os.path.join(os.path.dirname(__file__), "test_cases.json")

# V1 prompt: no few-shot examples, simpler rules
_V1_SYSTEM = (
    "You are a SQL expert. Convert the user's question into a valid SQLite SELECT query. "
    "Return ONLY the raw SQL query. No explanation, no markdown, no code fences. "
    "If the question cannot be answered from the given table, return exactly: INVALID_QUESTION"
)

_V1_TEMPLATE = (
    "Table name: {table_name}\n"
    "Columns:\n{schema_block}\n\n"
    "Only use SELECT. Use exact column names. Add LIMIT 100.\n\n"
    "User question: {question}\n"
    "SQL:"
)


def _generate_sql_v1(question, table_name, columns):
    """Simple prompt with no few-shot examples (V1 baseline)."""
    from backend.csv_processor import build_schema_block
    schema_block = build_schema_block(columns)
    user_prompt = _V1_TEMPLATE.format(
        table_name=table_name, schema_block=schema_block, question=question
    )
    response = _gen._get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _V1_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        max_tokens=300,
    )
    return _gen._clean_sql(response.choices[0].message.content.strip())


def run_pipeline(question, table_name, columns, generate_fn):
    """Run the pipeline with a given SQL generation function."""
    sql = generate_fn(question, table_name, columns)
    is_valid, error_msg = validate_sql(sql)
    if not is_valid:
        return sql, [], None, error_msg
    rows, exec_error = run_query(sql)
    if exec_error:
        return sql, [], None, exec_error
    answer = explain_result(question, rows)
    return sql, rows, answer, None


def score_case(case, sql, rows, error):
    """Return (passed: bool, reason: str)."""
    cat = case.get("category", "")

    if cat in ("safety", "out_of_scope"):
        if error:
            kws = case.get("expected_error_keywords", [])
            error_lower = error.lower()
            if all(kw.lower() in error_lower for kw in kws):
                return True, "Correctly returned error"
            return False, f"Error missing keywords {kws} — got: {error[:80]}"
        return False, "Expected an error but got rows"

    expected_kws = case.get("expected_sql_keywords", [])
    sql_upper = (sql or "").upper()
    missing = [kw for kw in expected_kws if kw.upper() not in sql_upper]

    if missing:
        return False, f"SQL missing keywords {missing} — SQL: {(sql or '')[:100]}"
    if case.get("expect_rows") and not rows:
        return False, f"Returned 0 rows — SQL: {(sql or '')[:100]}"

    return True, f"PASS ({len(rows)} rows)"


def main():
    parser = argparse.ArgumentParser(description="DataChat eval script")
    parser.add_argument(
        "--prompt-version", type=int, default=2, choices=[1, 2],
        help="1 = simple baseline prompt, 2 = full prompt with few-shot examples (default)"
    )
    args = parser.parse_args()

    version_label = f"V{args.prompt_version}"
    generate_fn = _generate_sql_v1 if args.prompt_version == 1 else _gen.generate_sql

    print("=" * 60)
    print(f"DataChat Evaluation — prompt version: {version_label}")
    print("=" * 60)

    print(f"\nLoading: {SAMPLE_CSV}")
    result = load_csv(SAMPLE_CSV)
    table_name = result["table_name"]
    columns = result["columns"]
    print(f"Table: {table_name} | Columns: {[c['name'] for c in columns]}\n")

    with open(TEST_CASES_PATH) as f:
        test_cases = json.load(f)

    passed = 0
    total = len(test_cases)

    for case in test_cases:
        cid = case["id"]
        question = case["question"]
        category = case.get("category", "")
        print(f"[{cid:02d}] [{category:<12}] {question}")
        try:
            sql, rows, answer, error = run_pipeline(question, table_name, columns, generate_fn)
        except Exception as e:
            sql, rows, answer, error = "", [], None, f"EXCEPTION: {e}"

        ok, reason = score_case(case, sql, rows, error)
        if ok:
            passed += 1
        status = "PASS" if ok else "FAIL"
        print(f"       {status}: {reason}")
        if not ok and sql:
            print(f"       SQL: {sql[:110]}")

    print("\n" + "=" * 60)
    accuracy = passed / total * 100
    print(f"RESULT ({version_label}): {passed}/{total} correct = {accuracy:.1f}%")
    print("=" * 60)
    return accuracy


if __name__ == "__main__":
    main()
