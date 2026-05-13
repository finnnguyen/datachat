import json
import os
from openai import OpenAI

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), timeout=30.0)
    return _client

_SYSTEM = (
    "You are a helpful data analyst. Answer the user's question in plain English "
    "using the query results provided. Be specific: use real numbers and names from the data. "
    "Do not mention SQL, databases, tables, or technical terms."
)


def explain_result(question: str, rows: list[dict]) -> str:
    """
    Call the LLM to turn query rows into a plain-English answer.
    """
    if not rows:
        return "No records matched your query. Try broadening your search or check that the values you're filtering on exist in the dataset."

    rows_preview = rows[:20]  # send at most 20 rows to keep prompt small
    rows_json = json.dumps(rows_preview, indent=2)

    prompt = (
        f'The user asked: "{question}"\n\n'
        f"The data returned:\n{rows_json}\n\n"
        f"Write a clear, specific 2–4 sentence answer in plain English.\n"
        f"- Lead with the most interesting finding.\n"
        f"- Use actual numbers and names from the results.\n"
        f"- If there are many rows, summarize the pattern rather than listing everything.\n"
        f"- Do not mention SQL or technical terms."
    )

    response = _get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=250,
    )

    return response.choices[0].message.content.strip()
