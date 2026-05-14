# DataChat — Ask Your CSV in Plain English

Upload a CSV dataset, ask questions in plain English, and get a written answer plus a chart — powered by GPT-4o-mini and SQLite.

## What it does

DataChat converts natural-language questions about tabular data into SQL, executes the query against a local SQLite database, and returns:
- A **plain-English answer** summarizing the result
- A **chart** (bar or line) when the result is a grouping or time series
- The **generated SQL** as a citation, so you can verify the query
- A scrollable **data table** of the raw results

The pipeline goes beyond a single LLM call: question → SQL generation (LLM) → safety validation (code) → SQL execution (SQLite) → result explanation (LLM) → chart rendering (matplotlib). If SQL execution fails, the app automatically retries with the error fed back to the LLM for self-correction.

## Setup

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd cpsc254_final_project

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your OpenAI API key
cp .env.example .env
# Open .env and replace "your_key_here" with your actual OPENAI_API_KEY

# 5. Start the app
python app.py
```

Open **http://localhost:5001** in your browser.

> **macOS note:** Port 5000 is reserved by AirPlay Receiver on macOS Monterey and later. The app runs on port 5001 to avoid this conflict.

> **Note:** Each server restart clears active sessions. Re-upload your CSV after restarting.

## How to use

1. **Upload a CSV** — click the upload box or drag a file onto it. Sample datasets are included:
   - `data/samples/sales.csv` — 100 rows: region, product, revenue, date, units_sold
   - `data/samples/housing.csv` — 100 rows: city, bedrooms, price, sqft, year_built
   - `data/samples/spotify.csv` — 100 rows: track, artist, streams, genre, year

2. **Check the schema panel** — column names and types are shown so you know what to ask.

3. **Ask a question** — type in plain English and press Enter or click Ask.

## Example questions (using sales.csv)

```
What is the total revenue by region?
What are the top 5 products by revenue?
Which products have been sold more than 3 times?
Show all Electronics sales in the South region.
What is the average revenue per sale?
Which sales had more than 50 units sold?
Show all sales from 2023.
What is the maximum revenue from a single sale?
```

## Running the evaluation

The eval script tests 12 labeled cases against the text-to-SQL pipeline using `sales.csv`.

```bash
# V1 baseline — simple prompt, no few-shot examples
python eval/eval.py --prompt-version 1

# V2 — full prompt with few-shot SQL examples
python eval/eval.py --prompt-version 2

# Default (same as V2)
python eval/eval.py
```

Output shows pass/fail per case and an overall accuracy percentage.

## Project structure

```
cpsc254_final_project/
├── app.py                   Flask routes + self-correction retry loop
├── backend/
│   ├── csv_processor.py     CSV → SQLite, schema detection, column sanitization
│   ├── sql_generator.py     LLM call 1: schema + question → SQL
│   ├── sql_validator.py     Keyword blocklist safety check
│   ├── sql_executor.py      sqlite3 query runner
│   ├── explainer.py         LLM call 2: rows → plain-English answer
│   └── chart_generator.py  matplotlib bar/line chart → base64 PNG
├── static/
│   ├── style.css
│   └── script.js
├── templates/
│   └── index.html
├── data/samples/            Sample CSVs committed to repo
├── eval/
│   ├── eval.py              Accuracy scorer (supports --prompt-version 1 or 2)
│   └── test_cases.json      12 labeled test cases
├── .env.example
├── requirements.txt
└── REPORT.md
```

## Requirements

- Python 3.11+
- `OPENAI_API_KEY` (only external dependency)
- All other dependencies are local (SQLite, matplotlib, Flask)
