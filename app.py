import os
import uuid
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, render_template, send_from_directory
from backend.csv_processor import load_csv, build_schema_block
from backend.sql_generator import generate_sql
from backend.sql_validator import validate_sql
from backend.sql_executor import run_query
from backend.explainer import explain_result
from backend.chart_generator import make_chart

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB

os.makedirs("data/uploads", exist_ok=True)

# In-memory session store: session_id → {table_name, columns}
_sessions: dict = {}


@app.errorhandler(Exception)
def handle_exception(e):
    """Return JSON instead of HTML for any unhandled exception."""
    return jsonify({"error": f"Server error: {e}"}), 500


@app.route("/data/samples/<path:filename>")
def serve_sample(filename):
    return send_from_directory("data/samples", filename)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided."}), 400

    f = request.files["file"]
    if not f.filename or not f.filename.lower().endswith(".csv"):
        return jsonify({"error": "Please upload a CSV file."}), 400

    session_id = str(uuid.uuid4())
    tmp_path = f"data/uploads/{session_id}.csv"
    f.save(tmp_path)

    try:
        result = load_csv(tmp_path, original_name=f.filename)
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return jsonify({"error": f"Could not read CSV: {e}"}), 400

    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    _sessions[session_id] = {
        "table_name": result["table_name"],
        "columns": result["columns"],
    }

    return jsonify({
        "session_id": session_id,
        "table_name": result["table_name"],
        "columns": result["columns"],
    })


@app.route("/query", methods=["POST"])
def query():
    try:
        data = request.get_json(force=True)
        question = (data.get("question") or "").strip()
        session_id = data.get("session_id") or ""

        if not question:
            return jsonify({"error": "Please enter a question."}), 400

        if session_id not in _sessions:
            return jsonify({"error": "Session expired — please upload your CSV again."}), 400

        session = _sessions[session_id]
        table_name = session["table_name"]
        columns = session["columns"]

        # Step 1: generate SQL
        try:
            sql = generate_sql(question, table_name, columns)
        except Exception as e:
            return jsonify({"error": f"Failed to generate SQL: {e}"})

        # Step 2: validate
        is_valid, error_msg = validate_sql(sql)
        if not is_valid:
            return jsonify({"error": error_msg, "sql": sql if sql.upper() != "INVALID_QUESTION" else None})

        # Step 3: execute
        rows, exec_error = run_query(sql)
        if exec_error:
            # Retry once: send the error back to the LLM for self-correction
            retry_sql = _retry_sql(table_name, columns, sql, exec_error)
            if retry_sql:
                rows, exec_error = run_query(retry_sql)
                sql = retry_sql
            if exec_error:
                return jsonify({"error": exec_error, "sql": sql})

        # Step 4: chart
        chart_b64 = make_chart(rows)

        # Step 5: explain
        try:
            answer = explain_result(question, rows)
        except Exception:
            answer = "(Could not generate a text explanation.)"

        return jsonify({"sql": sql, "rows": rows, "answer": answer, "chart_b64": chart_b64})

    except Exception as e:
        return jsonify({"error": f"Unexpected error: {e}"}), 500


def _retry_sql(table_name, columns, failed_sql, error_msg):
    """Ask the LLM to fix a failed SQL query. Returns corrected SQL or None."""
    from backend.sql_generator import _get_client, _clean_sql
    schema_block = build_schema_block(columns)
    prompt = (
        f"The following SQLite query failed.\n\n"
        f"Table: {table_name}\nColumns:\n{schema_block}\n\n"
        f"Failed query:\n{failed_sql}\n\n"
        f"Error: {error_msg}\n\n"
        f"Fix the query. Return ONLY the corrected SQL, no explanation, no markdown."
    )
    try:
        response = _get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=300,
        )
        fixed = _clean_sql(response.choices[0].message.content.strip())
        is_valid, _ = validate_sql(fixed)
        return fixed if is_valid else None
    except Exception:
        return None


if __name__ == "__main__":
    app.run(debug=False, port=5000)
