# FinAgent 🤖📈
> An AI-powered financial analysis agent that thinks like an analyst, not a dashboard.

---

## What is FinAgent?

FinAgent is an intelligent financial analysis system that fetches raw company financials, computes key metrics, scores business quality, and generates plain-English analyst verdicts — all via a REST API.

Unlike traditional tools like Groww or Tickertape that show you numbers and leave you to figure out what they mean, FinAgent **reasons across metrics** and tells you what the numbers actually say about a business.

---

## Architecture

```
Alpha Vantage API
      ↓
DataAgent          — fetches raw financials (income, balance, cashflow, overview)
      ↓
MemoryLayer        — caches everything (in-memory + MongoDB + ChromaDB)
      ↓
MetricsAgent       — computes ratios (ROE, margins, growth, debt metrics)
      ↓
ScoringEngine      — scores Profitability / Growth / Safety → overall grade
      ↓
LLMAgent           — Gemini generates verdicts, recommendations, comparisons
      ↓
FastAPI            — REST API exposes everything as endpoints
```

---

## Project Structure

```
finagent/
├── dataagent/
│   └── dataagent.py          # Fetches raw data from Alpha Vantage
├── memory/
│   └── memorylayer.py        # In-memory + MongoDB + ChromaDB cache
├── matrixagent/
│   └── MatrixCompAGENT.py    # Computes all financial ratios
├── scoreengine/
│   └── scoreEngine.py        # Scores and grades metrics
├── llmagent/
│   └── LLMAgentComp.py       # Gemini-powered analyst agent
├── app.py                    # FastAPI server
├── main.py                   # CLI entry point
├── .env                      # API keys (never commit this)
└── requirements.txt
```

---

## Metrics Computed

### Profitability `weight = 40%`
| Metric | Source |
|---|---|
| Return on Equity (ROE) | Net Income / Total Equity |
| Net Profit Margin | Net Income / Revenue |
| Operating Margin | Operating Income / Revenue |
| Asset Turnover | Revenue / Total Assets |

### Growth `weight = 35%`
| Metric | Source |
|---|---|
| Revenue Growth YoY | (Rev₀ - Rev₁) / Rev₁ |
| FCF Growth YoY | (FCF₀ - FCF₁) / FCF₁ |

### Safety `weight = 25%`
| Metric | Source |
|---|---|
| Current Ratio | Current Assets / Current Liabilities |
| Debt to Equity | Total Debt / Total Equity |
| Interest Coverage | EBITDA / Interest Expense |
| Free Cash Flow | Operating CF - CapEx |

---

## Scoring System

Each metric is scored 0–100 using a threshold ladder and weighted within its category. Categories are then weighted to produce an overall score.

```
Score → Grade
──────────────
90+   →  A+  Exceptional
80+   →  A   Strong
70+   →  B+  Above Average
60+   →  B   Decent
50+   →  C+  Mixed
40+   →  C   Below Average
30+   →  D   Weak
0+    →  F   Poor / Avoid
```

### Cross-Metric Flags
The engine also detects traps that individual scores miss:

- 🔴 High margin + negative FCF → earnings quality concern
- 🟡 Revenue growing + thin margins → scalability risk
- 🔴 High leverage + low interest coverage → solvency risk
- 🔴 Current ratio below 1.0 → liquidity risk
- ✅ Strong across all three categories → high conviction candidate

---



## API Endpoints



### `GET /analyze/{symbol}`
Full pipeline — fetch, score, LLM verdict, recommendation in one call.
```json
{
  "symbol": "AAPL",
  "fiscal_year": "2023-09-30",
  "score": { "overall_score": 74.2, "grade": "B+", ... },
  "metrics": { "roe": 1.47, "profit_margin": 0.253, ... },
  "verdict": "Apple's profitability is exceptional...",
  "recommendation": { "action": "HOLD", "conviction": "MEDIUM", ... }
}
```

### `GET /score/{symbol}`
Score only — no LLM call. Fast, use for dashboards.

### `GET /verdict/{symbol}`
Plain English analyst verdict from Gemini.

### `GET /recommend/{symbol}`
Structured buy / hold / avoid recommendation.
```json
{
  "action": "BUY",
  "conviction": "HIGH",
  "reasoning": "Strong FCF growth and margin expansion...",
  "risks": "Current ratio below 1.0 warrants monitoring.",
  "one_liner": "A quality compounder trading at a reasonable price."
}
```

### `POST /compare`
Head to head comparison of two companies.
```json
// Request
{ "symbol_a": "AAPL", "symbol_b": "MSFT" }

// Response
{
  "score_a": { ... },
  "score_b": { ... },
  "comparison": "Microsoft edges out Apple on safety..."
}
```

### `GET /chat/{symbol}?q=your question`
Ask any follow-up question about a stock.
```
/chat/AAPL?q=Why is the safety score low?
/chat/TSLA?q=Is the debt level dangerous?
/chat/MSFT?q=What would improve the growth score?
```

---

## Memory Layer

FinAgent uses a three-tier memory system:

```
Tier 1 — In-Memory Cache     fastest, expires on restart
Tier 2 — MongoDB             persistent, survives restarts


Every piece of data is stored with a key convention:
```
{SYMBOL}_OVERVIEW    company metadata
{SYMBOL}_INCOME      income statement (3 years)
{SYMBOL}_BALANCE     balance sheet (3 years)
{SYMBOL}_CASHFLOW    cash flow (3 years)
{SYMBOL}_METRICS     computed ratios
{SYMBOL}_SCORE       scoring engine output
{SYMBOL}_VERDICT     LLM analyst verdict
{SYMBOL}_RECOMMEND   buy/hold/avoid recommendation
```

Second call for the same symbol is **instant** — no API hit.

---

## Setup

### 1. Clone and install
```bash
git clone https://github.com/yourname/finagent.git
cd finagent
pip install -r requirements.txt
```

### 2. Environment variables
Create a `.env` file:
```env
Alpha_vantage_API-Key=your_alphavantage_key
gemini_API-Key=your_gemini_key
mongo_uri=mongodb://localhost:27017/
mongo_db_name=finagent
```

### 3. Run the API
```bash
uvicorn app:app --reload
```

### 4. Or run the CLI
```bash
python main.py
# → Enter a stock symbol: AAPL
```

Interactive docs available at: `http://localhost:8000/docs`

---

## Requirements

```
fastapi
uvicorn
python-dotenv
requests
pymongo
chromadb
sentence-transformers
google-generativeai
```

---

## How FinAgent Differs from Traditional Tools

| Feature | Groww / Tickertape | FinAgent |
|---|---|---|
| Shows financial data | ✅ | ✅ |
| Connects metrics together | ❌ | ✅ |
| Weighted scoring system | ❌ | ✅ |
| Cross-metric red flags | ❌ | ✅ |
| Plain English verdict | ❌ | ✅ |
| Ask follow-up questions | ❌ | ✅ |
| Head to head comparison | ❌ | ✅ |
| Memory across requests | ❌ | ✅ |
| Open REST API | ❌ | ✅ |
| Custom scoring weights | ❌ | ✅ |

> Traditional tools are dashboards. FinAgent is a financial analyst you can talk to.

---




