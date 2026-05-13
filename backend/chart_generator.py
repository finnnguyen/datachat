import base64
import io
from typing import Optional
import matplotlib
matplotlib.use("Agg")  # non-interactive backend, required for Flask
import matplotlib.pyplot as plt

MAX_BARS = 15  # truncate bar charts beyond this to keep labels readable


def make_chart(rows: list) -> Optional[str]:
    """
    Generate a chart for 2-column query results only.
    Returns a base64-encoded PNG string, or None if no chart is appropriate.
    """
    if not rows or len(rows) < 2:
        return None

    cols = list(rows[0].keys())

    # Only chart clean 2-column results (e.g. GROUP BY aggregations)
    if len(cols) != 2:
        return None

    col_a, col_b = cols
    values_b = [r[col_b] for r in rows]

    if not _is_numeric(values_b):
        return None

    # Truncate to MAX_BARS to avoid illegible labels
    display_rows = rows[:MAX_BARS]
    labels = [str(r[col_a]) for r in display_rows]
    values = [float(r[col_b]) if r[col_b] is not None else 0 for r in display_rows]

    if _looks_like_date(labels[0]):
        return _line_chart(labels, values, col_a, col_b)
    return _bar_chart(labels, values, col_a, col_b)


def _is_numeric(values: list) -> bool:
    try:
        [float(v) for v in values if v is not None]
        return True
    except (TypeError, ValueError):
        return False


def _looks_like_date(value: str) -> bool:
    import re
    return bool(re.match(r"\d{4}[-/]\d{2}", str(value)))


def _bar_chart(labels: list, values: list, xlabel: str, ylabel: str) -> str:
    fig, ax = plt.subplots(figsize=(8, 4))
    x = range(len(labels))
    ax.bar(x, values, color="#4F8EF7", edgecolor="white", linewidth=0.5)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_title(f"{ylabel} by {xlabel}", fontsize=12, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _fig_to_b64(fig)


def _line_chart(labels: list, values: list, xlabel: str, ylabel: str) -> str:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(labels, values, marker="o", color="#4F8EF7", linewidth=2, markersize=5)
    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_title(f"{ylabel} over {xlabel}", fontsize=12, fontweight="bold")
    ax.tick_params(axis="x", rotation=30)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _fig_to_b64(fig)


def _fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")
