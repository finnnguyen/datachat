# DataChat — Ask Your CSV in Plain English

Upload a CSV, ask a question in plain English, get a written answer and a chart. Powered by GPT-4o-mini and SQLite.

**Tech:** Python · Flask · OpenAI GPT-4o-mini · SQLite · pandas · matplotlib · HTML · CSS · JavaScript

---

## What it does

DataChat converts a natural-language question about tabular data into SQL, executes it against a local SQLite database, and returns:

- A **plain-English answer** summarizing the result
- A **chart** (bar or line) when the result is a grouping or time series
- The **generated SQL** as a citation so you can verify the query
- A scrollable **data table** of the raw results

The pipeline goes beyond a single LLM call:

```
Question → SQL generation (LLM #1) → safety validation → SQL execution (SQLite)
→ result explanation (LLM #2) → chart rendering (matplotlib)
```

If SQL execution fails, the app automatically retries with the error fed back to the model for self-correction.

---

## Prompt engineering & evaluation

The text-to-SQL prompt was iterated across 3 versions using a 12-case labeled eval suite (`eval/test_cases.json`):

| Version | Change | Accuracy |
|---|---|---|
| V1 | Basic rules only, no examples | 8/12 — **66.7%** |
| V2 | Added 4 few-shot SQL examples (COUNT, GROUP BY, HAVING, ORDER BY LIMIT) | 10/12 — **83.3%** |
| V3 | Added AVG example, fixed safety test scoring | 12/12 — **100%** |

Run the eval yourself:

```bash
python eval/eval.py --prompt-version 1   # V1 baseline
python eval/eval.py --prompt-version 2   # V2 few-shot
python eval/eval.py                      # V3 (default)
```

---

## Safety

- **Prompt injection:** CSV column names are sanitized (letters, numbers, underscores only) before entering the LLM prompt — prevents malicious column names from hijacking the model
- **SQL validation:** Any output that doesn't start with `SELECT` or contains blocked keywords (`DROP`, `DELETE`, `INSERT`, etc.) is rejected before execution

---

## Setup

```bash
git clone https://github.com/finnnguyen/datachat.git
cd datachat

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Add your OPENAI_API_KEY to .env

python app.py
```

Open **http://localhost:5001**

> macOS note: port 5001 is used to avoid AirPlay Receiver on port 5000.

---

## Sample datasets

Three CSVs are included in `data/samples/` to try right away:

| File | Rows | Columns |
|---|---|---|
| `sales.csv` | 100 | region, product, revenue, date, units_sold |
| `housing.csv` | 100 | city, bedrooms, price, sqft, year_built |
| `spotify.csv` | 100 | track, artist, streams, genre, year |

Example questions:
```
What is the total revenue by region?
Which products have been sold more than 3 times?
What is the average revenue per sale?
Show all Electronics sales in the South region.
```

---

## Project structure

```
datachat/
├── app.py                   Flask routes + self-correction retry loop
├── backend/
│   ├── csv_processor.py     CSV → SQLite, schema detection, column sanitization
│   ├── sql_generator.py     LLM call 1: schema + question → SQL (few-shot prompt)
│   ├── sql_validator.py     Keyword blocklist safety check
│   ├── sql_executor.py      sqlite3 query runner
│   ├── explainer.py         LLM call 2: rows → plain-English answer
│   └── chart_generator.py   matplotlib bar/line chart → base64 PNG
├── static/
│   ├── style.css
│   └── script.js
├── templates/
│   └── index.html
├── data/samples/            Sample CSVs (sales, housing, spotify)
├── eval/
│   ├── eval.py              Accuracy scorer (--prompt-version 1 or 2)
│   └── test_cases.json      12 labeled test cases
├── .env.example
├── requirements.txt
└── REPORT.md
```

---

## Built by

**Finn Nguyen** — CPSC 254 · Cal State Fullerton

---

[→ Featured on my portfolio](https://finn-portfolio-phi.vercel.app)
