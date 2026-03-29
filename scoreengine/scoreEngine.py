"""
scoring_engine.py
─────────────────
Scores metrics produced by MetricsAgent.

Expects these keys from MetricsAgent.compute_metrics():
    profit_margin, roe, operating_margin, asset_turnover   → Profitability
    revenue_growth, fcf_growth                             → Growth
    debt_to_equity, current_ratio, interest_coverage,
    free_cash_flow                                         → Safety

Note: margin/growth values are decimals (e.g. 0.25 = 25%)
      ratios like current_ratio, debt_to_equity are plain multiples
"""

import datetime
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────

CATEGORY_WEIGHTS = {
    "profitability": 0.40,
    "growth":        0.35,
    "safety":        0.25,
}

# Thresholds match MetricsAgent scale:
# margins/growth = decimals | ratios = multiples | fcf = absolute $

RUBRICS = {
    "profitability": {
        "roe": {
            "weight":     0.35,
            "thresholds": [0.20, 0.15, 0.10, 0.05],
            "scores":     [100,  75,   50,   25,  0],
            "label":      "Return on Equity",
            "fmt":        "pct",
        },
        "profit_margin": {
            "weight":     0.30,
            "thresholds": [0.20, 0.12, 0.06, 0.02],
            "scores":     [100,  75,   50,   25,  0],
            "label":      "Net Profit Margin",
            "fmt":        "pct",
        },
        "operating_margin": {
            "weight":     0.20,
            "thresholds": [0.25, 0.15, 0.08, 0.03],
            "scores":     [100,  75,   50,   25,  0],
            "label":      "Operating Margin",
            "fmt":        "pct",
        },
        "asset_turnover": {
            "weight":     0.15,
            "thresholds": [1.5, 1.0, 0.6, 0.3],
            "scores":     [100, 75,  50,  25,  0],
            "label":      "Asset Turnover",
            "fmt":        "x",
        },
    },

    "growth": {
        "revenue_growth": {
            "weight":     0.50,
            "thresholds": [0.20, 0.12, 0.06, 0.0],
            "scores":     [100,  75,   50,   25,  0],
            "label":      "Revenue Growth YoY",
            "fmt":        "pct",
        },
        "fcf_growth": {
            "weight":     0.50,
            "thresholds": [0.25, 0.15, 0.05, 0.0],
            "scores":     [100,  75,   50,   25,  0],
            "label":      "FCF Growth YoY",
            "fmt":        "pct",
        },
    },

    "safety": {
        "current_ratio": {
            "weight":     0.25,
            "thresholds": [2.0, 1.5, 1.0, 0.7],
            "scores":     [100, 75,  50,  25,  0],
            "label":      "Current Ratio",
            "fmt":        "x",
        },
        "debt_to_equity": {
            "weight":     0.35,
            "thresholds": [0.3, 0.7, 1.5, 3.0],   # lower = better
            "scores":     [100, 75,  50,  25,  0],
            "label":      "Debt to Equity",
            "fmt":        "x",
            "inverted":   True,
        },
        "interest_coverage": {
            "weight":     0.25,
            "thresholds": [10,  5,  3,  1.5],
            "scores":     [100, 75, 50, 25,  0],
            "label":      "Interest Coverage",
            "fmt":        "x",
        },
        "free_cash_flow": {
            "weight":     0.15,
            "thresholds": [1e9, 0, -5e8, -1e9],
            "scores":     [100, 75,  25,   0,  0],
            "label":      "Free Cash Flow",
            "fmt":        "abs",
        },
    },
}

GRADE_MAP = [
    (90, "A+", "Exceptional"),
    (80, "A",  "Strong"),
    (70, "B+", "Above Average"),
    (60, "B",  "Decent"),
    (50, "C+", "Mixed"),
    (40, "C",  "Below Average"),
    (30, "D",  "Weak"),
    (0,  "F",  "Poor / Avoid"),
]


# ─────────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────────

@dataclass
class MetricResult:
    key:       str
    label:     str
    value:     Optional[float]
    score:     float
    weight:    float
    formatted: str = ""


@dataclass
class CategoryScore:
    name:          str
    score:         float
    grade:         str
    descriptor:    str
    metrics:       list = field(default_factory=list)
    missing_count: int  = 0


@dataclass
class OverallScore:
    symbol:        str
    fiscal_year:   str
    overall_score: float
    grade:         str
    descriptor:    str
    categories:    dict = field(default_factory=dict)
    flags:         list = field(default_factory=list)
    generated_at:  str  = ""


# ─────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────

def _score_value(value: float, thresholds: list, scores: list,
                 inverted: bool = False) -> float:
    if inverted:
        for i, t in enumerate(thresholds):
            if value <= t:
                return float(scores[i])
    else:
        for i, t in enumerate(thresholds):
            if value >= t:
                return float(scores[i])
    return float(scores[-1])


def _grade(score: float) -> tuple:
    for threshold, grade, desc in GRADE_MAP:
        if score >= threshold:
            return grade, desc
    return "F", "Poor / Avoid"


def _fmt(value: float, fmt: str) -> str:
    if value is None:
        return "N/A"
    if fmt == "pct":
        return f"{value * 100:.1f}%"
    if fmt == "x":
        return f"{value:.2f}x"
    if fmt == "abs":
        if abs(value) >= 1e9:
            return f"${value / 1e9:.2f}B"
        if abs(value) >= 1e6:
            return f"${value / 1e6:.1f}M"
        return f"${value:,.0f}"
    return str(round(value, 3))


def _score_category(cat_name: str, metrics: dict) -> CategoryScore:
    rubric       = RUBRICS[cat_name]
    weighted_sum = 0.0
    weight_used  = 0.0
    results      = []
    missing      = 0

    for key, cfg in rubric.items():
        value    = metrics.get(key)
        inverted = cfg.get("inverted", False)

        if value is None:
            missing += 1
            results.append(MetricResult(
                key=key, label=cfg["label"], value=None,
                score=0, weight=cfg["weight"], formatted="N/A"
            ))
            continue

        raw_score     = _score_value(float(value), cfg["thresholds"],
                                     cfg["scores"], inverted)
        weighted_sum += raw_score * cfg["weight"]
        weight_used  += cfg["weight"]

        results.append(MetricResult(
            key=key,
            label=cfg["label"],
            value=float(value),
            score=raw_score,
            weight=cfg["weight"],
            formatted=_fmt(float(value), cfg["fmt"]),
        ))

    cat_score   = (weighted_sum / weight_used) if weight_used else 0.0
    grade, desc = _grade(cat_score)

    return CategoryScore(
        name=cat_name.capitalize(),
        score=round(cat_score, 1),
        grade=grade,
        descriptor=desc,
        metrics=results,
        missing_count=missing,
    )


def _detect_flags(metrics: dict, cats: dict) -> list:
    flags = []

    pm  = metrics.get("profit_margin")     or 0
    fcf = metrics.get("free_cash_flow")    or 0
    dte = metrics.get("debt_to_equity")    or 0
    ic  = metrics.get("interest_coverage") or 999
    cr  = metrics.get("current_ratio")     or 2
    rg  = metrics.get("revenue_growth")    or 0
    om  = metrics.get("operating_margin")  or 0

    if pm > 0.10 and fcf < 0:
        flags.append("🔴 High margin but negative FCF — earnings quality concern")
    if rg > 0.10 and om < 0.05:
        flags.append("🟡 Revenue growing but margins thin — scalability risk")
    if dte > 2.0 and ic < 3:
        flags.append("🔴 High leverage + low interest coverage — solvency risk")
    if cr < 1.0:
        flags.append("🔴 Current ratio below 1.0 — short-term liquidity risk")

    p = cats.get("profitability", CategoryScore("", 0, "", "")).score
    g = cats.get("growth",        CategoryScore("", 0, "", "")).score
    s = cats.get("safety",        CategoryScore("", 0, "", "")).score
    if p > 75 and g > 70 and s > 70:
        flags.append("✅ Strong across all three categories — high conviction candidate")

    return flags


# ─────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────

def score_company(symbol: str, memory) -> OverallScore:
    """
    Main entry point.

    Pulls metrics from MemoryLayer using key: {symbol}_METRICS
    That key is written by MetricsAgent.compute_metrics().

    Usage:
        result = score_company("AAPL", memory)
        print_score_report(result)
    """
    metrics_key = f"{symbol}_METRICS"
    metrics     = memory.retrieve(metrics_key)

    if not metrics:
        raise ValueError(
            f"[ScoringEngine] No metrics found for '{symbol}' in memory. "
            f"Run MetricsAgent.compute_metrics('{symbol}') first."
        )

    categories       = {}
    overall_weighted = 0.0

    for cat_name, cat_weight in CATEGORY_WEIGHTS.items():
        cat = _score_category(cat_name, metrics)
        categories[cat_name] = cat
        overall_weighted    += cat.score * cat_weight

    overall     = round(overall_weighted, 1)
    grade, desc = _grade(overall)
    flags       = _detect_flags(metrics, categories)

    result = OverallScore(
        symbol=metrics.get("symbol", "N/A"),
        fiscal_year=metrics.get("fiscal_year", "N/A"),
        overall_score=overall,
        grade=grade,
        descriptor=desc,
        categories=categories,
        flags=flags,
        generated_at=str(datetime.datetime.utcnow()),
    )

    # store result back in memory for downstream use (e.g. LLM summary layer)
    memory.store(f"{symbol}_SCORE", {
        "symbol":        result.symbol,
        "fiscal_year":   result.fiscal_year,
        "overall_score": result.overall_score,
        "grade":         result.grade,
        "descriptor":    result.descriptor,
        "flags":         result.flags,
        "generated_at":  result.generated_at,
    }, data_type="score")

    return result


# ─────────────────────────────────────────────────────────────
# REPORT PRINTER
# ─────────────────────────────────────────────────────────────

def print_score_report(result: OverallScore):
    bar = lambda s: ("█" * int(s / 5)).ljust(20) + f"  {s:.1f}/100"

    print("\n" + "═" * 58)
    print(f"  FinAgent Report — {result.symbol}  (FY: {result.fiscal_year})")
    print("═" * 58)
    print(f"  Overall  :  {result.overall_score:.1f} / 100   [{result.grade}] {result.descriptor}")
    print("─" * 58)

    for cat_key, cat in result.categories.items():
        w = int(CATEGORY_WEIGHTS[cat_key] * 100)
        print(f"\n  {cat.name}  (weight={w}%)  [{cat.grade}] {cat.descriptor}")
        print(f"  {bar(cat.score)}")
        for m in cat.metrics:
            print(f"    • {m.label:<26}  {m.formatted:>10}   score={m.score:.0f}")
        if cat.missing_count:
            print(f"    ⚠️  {cat.missing_count} metric(s) missing")

    if result.flags:
        print("\n" + "─" * 58)
        print("  Flags:")
        for f in result.flags:
            print(f"    {f}")

    print("\n" + "═" * 58 + "\n")

      