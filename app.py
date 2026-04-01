"""
app.py
──────
FastAPI server for FinAgent.

Endpoints:
    GET  /analyze/{symbol}         — full pipeline (fetch + score + verdict + recommend)
    GET  /score/{symbol}           — score only
    GET  /verdict/{symbol}         — LLM plain English verdict
    GET  /recommend/{symbol}       — buy / hold / avoid
    POST /compare                  — head to head two symbols
    GET  /chat/{symbol}?q=...      — follow-up question

Run:
    uvicorn app:app --reload
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dataagent.dataagent             import DataAgent
from memory.memorylayer              import MemoryLayer
from matrixagent.MatrixCompAGENT     import MetricsAgent
from llmagent.LLMAgentComp           import LLMAgent
from scoreengine.scoreEngine         import score_company, print_score_report

load_dotenv()


# ─────────────────────────────────────────────────────────────
# APP INIT
# ─────────────────────────────────────────────────────────────

memory       = None
data_agent   = None
metrics_agent= None
llm_agent    = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all agents once at startup."""
    global memory, data_agent, metrics_agent, llm_agent

    memory        = MemoryLayer(os.getenv("mongo_uri"), os.getenv("mongo_db_name"))
    data_agent    = DataAgent(api_key=os.getenv("Alpha_vantage_API-Key"), memory=memory)
    metrics_agent = MetricsAgent(memory=memory)
    llm_agent     = LLMAgent(api_key=os.getenv("gemini_API-Key"), memory=memory)

    print("✅ All agents initialized.")
    yield
    print("🛑 Shutting down.")


app = FastAPI(
    title="FinAgent API",
    description="AI-powered financial analysis agent",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# ─────────────────────────────────────────────────────────────

class CompareRequest(BaseModel):
    symbol_a: str
    symbol_b: str


class ChatRequest(BaseModel):
    question: str


# ─────────────────────────────────────────────────────────────
# SHARED PIPELINE HELPER
# ─────────────────────────────────────────────────────────────

def _ensure_data(symbol: str):
    """
    Fetch + compute metrics for a symbol if not already in memory.
    Uses check_key to avoid redundant API calls.
    """
    symbol = symbol.upper()

    if not memory.check_key(f"{symbol}_OVERVIEW"):
        data_agent.fetch_company_overview(symbol)

    if not memory.check_key(f"{symbol}_INCOME"):
        data_agent.fetch_income_statement(symbol)

    if not memory.check_key(f"{symbol}_BALANCE"):
        data_agent.fetch_balance_sheet(symbol)

    if not memory.check_key(f"{symbol}_CASHFLOW"):
        data_agent.fetch_cash_flow(symbol)

    if not memory.check_key(f"{symbol}_METRICS"):
        metrics_agent.compute_metrics(symbol)

    if not memory.check_key(f"{symbol}_SCORE"):
        score_company(symbol, memory)


def _safe_run(symbol: str, fn):
    """Wrap pipeline calls in consistent error handling."""
    try:
        symbol = symbol.upper()
        _ensure_data(symbol)
        return fn(symbol)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────

@app.get("/analyze/{symbol}", summary="Full pipeline — fetch, score, verdict, recommend")
def analyze(symbol: str):
    """
    Runs the complete pipeline for a symbol:
    fetch → metrics → score → LLM verdict → recommendation
    Returns everything in one response.
    """
    try:
        symbol = symbol.upper()
        _ensure_data(symbol)

        metrics = memory.retrieve(f"{symbol}_METRICS")
        score   = memory.retrieve(f"{symbol}_SCORE")
        verdict = llm_agent.verdict(symbol)
        rec     = llm_agent.recommend(symbol)

        return {
            "symbol":         symbol,
            "fiscal_year":    metrics.get("fiscal_year"),
            "score":          score,
            "metrics":        metrics,
            "verdict":        verdict,
            "recommendation": rec,
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/score/{symbol}", summary="Score only — no LLM")
def get_score(symbol: str):
    """
    Returns category scores + overall grade without calling the LLM.
    Fast and cheap — use this for dashboards.
    """
    def fn(s):
        metrics = memory.retrieve(f"{s}_METRICS")
        score   = memory.retrieve(f"{s}_SCORE")
        return {
            "symbol":      s,
            "fiscal_year": metrics.get("fiscal_year"),
            "metrics":     metrics,
            "score":       score,
        }
    return _safe_run(symbol, fn)


@app.get("/verdict/{symbol}", summary="LLM plain English analyst verdict")
def get_verdict(symbol: str):
    """
    Returns a plain English analyst verdict for a symbol.
    Calls Gemini — takes 2-4 seconds.
    """
    def fn(s):
        text = llm_agent.verdict(s)
        return {"symbol": s, "verdict": text}
    return _safe_run(symbol, fn)


@app.get("/recommend/{symbol}", summary="Buy / Hold / Avoid recommendation")
def get_recommendation(symbol: str):
    """
    Returns a structured buy / hold / avoid recommendation with
    conviction level, reasoning, risks, and a one-liner.
    """
    def fn(s):
        rec = llm_agent.recommend(s)
        return {"symbol": s, "recommendation": rec}
    return _safe_run(symbol, fn)


@app.post("/compare", summary="Head to head comparison of two symbols")
def compare(body: CompareRequest):
    """
    Compares two stocks head to head.
    Both symbols are fetched and scored if not already in memory.
    """
    try:
        a = body.symbol_a.upper()
        b = body.symbol_b.upper()

        _ensure_data(a)
        _ensure_data(b)

        comparison = llm_agent.compare(a, b)

        score_a = memory.retrieve(f"{a}_SCORE")
        score_b = memory.retrieve(f"{b}_SCORE")

        return {
            "symbol_a":   a,
            "symbol_b":   b,
            "score_a":    score_a,
            "score_b":    score_b,
            "comparison": comparison,
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat/{symbol}", summary="Ask a follow-up question about a stock")
def chat(
    symbol: str,
    q: str = Query(..., description="Your question about this stock")
):
    """
    Ask any follow-up question about a stock's score or financials.

    Examples:
        /chat/AAPL?q=Why is the safety score low?
        /chat/MSFT?q=What would improve the growth score?
        /chat/TSLA?q=Is the debt level dangerous?
    """
    def fn(s):
        answer = llm_agent.chat(s, q)
        return {"symbol": s, "question": q, "answer": answer}
    return _safe_run(symbol, fn)


# ─────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────

@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}