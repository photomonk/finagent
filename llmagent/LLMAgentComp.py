import datetime
import json
from google import genai
from typing import Optional

class LLMAgent:
    # Use 1.5-Flash for speed/cost, or 1.5-Pro for complex reasoning
    MODEL = "gemini-2.5-flash"

    def __init__(self, api_key: str, memory):
        # Initialize the new Client
        self.client = genai.Client(api_key=api_key)
        self.memory = memory
        
        # Define the persona once
        self.system_instruction = (
            "You are a senior equity analyst specializing in fundamental analysis. "
            "Your tone is professional, objective, and data-driven. Use precise "
            "financial terminology. Avoid generic openers and flowery language."
        )

    # ─────────────────────────────────────────────────────────
    # INTERNAL HELPERS
    # ─────────────────────────────────────────────────────────

    def _get_context(self, symbol: str) -> dict:
        metrics = self.memory.retrieve(f"{symbol}_METRICS")
        score = self.memory.retrieve(f"{symbol}_SCORE")
        if not metrics or not score:
            raise ValueError(f"Missing data for {symbol}. Ensure analysis agents have run.")
        return {"metrics": metrics, "score": score}

    def _fmt_context(self, symbol: str, ctx: dict) -> str:
        m, s = ctx["metrics"], ctx["score"]
        def pct(v): return f"{v*100:.1f}%" if v is not None else "N/A"
        def x(v):   return f"{v:.2f}x" if v is not None else "N/A"
        def usd(v):
            if v is None: return "N/A"
            if abs(v) >= 1e9: return f"${v/1e9:.2f}B"
            if abs(v) >= 1e6: return f"${v/1e6:.1f}M"
            return f"${v:,.0f}"

        return f"""
COMPANY: {symbol} | FY: {m.get('fiscal_year', 'N/A')}
OVERALL: {s.get('overall_score')}/100 [{s.get('grade')}] {s.get('descriptor')}
PROFITABILITY: ROE {pct(m.get('roe'))}, Margin {pct(m.get('profit_margin'))}
GROWTH: Revenue {pct(m.get('revenue_growth'))}, FCF {pct(m.get('fcf_growth'))}
SAFETY: Current {x(m.get('current_ratio'))}, D/E {x(m.get('debt_to_equity'))}, FCF {usd(m.get('free_cash_flow'))}
FLAGS: {', '.join(s.get('flags', [])) or 'None'}
""".strip()

    def _call(self, prompt: str, is_json: bool = False) -> str:
        """Helper updated for the new google-genai Client syntax."""
        
        # In the new SDK, we pass system_instruction inside the call or config
        response = self.client.models.generate_content(
            model=self.MODEL,
            contents=prompt,
            config={
                "system_instruction": self.system_instruction,
                "response_mime_type": "application/json" if is_json else "text/plain"
            }
        )
        return response.text.strip()

    # ─────────────────────────────────────────────────────────
    # PUBLIC METHODS
    # ─────────────────────────────────────────────────────────

    def verdict(self, symbol: str) -> str:
        ctx = self._get_context(symbol)
        context = self._fmt_context(symbol, ctx)
        prompt = f"Analyze the following data and write a concise, 4-6 sentence verdict.\n\n{context}"
        
        result = self._call(prompt)
        self.memory.store(f"{symbol}_VERDICT", result, ttl=3600)
        return result

    def compare(self, symbol_a: str, symbol_b: str) -> str:
        ctx_a, ctx_b = self._get_context(symbol_a), self._get_context(symbol_b)
        prompt = f"""
Compare {symbol_a} and {symbol_b} in 5-7 sentences. Identify the winner in profitability 
and safety, then state a clear preference.

--- {symbol_a} ---
{self._fmt_context(symbol_a, ctx_a)}

--- {symbol_b} ---
{self._fmt_context(symbol_b, ctx_b)}
"""
        result = self._call(prompt)
        self.memory.store(f"{symbol_a}_vs_{symbol_b}_COMPARE", result, ttl=3600)
        return result

    def recommend(self, symbol: str) -> dict:
        ctx = self._get_context(symbol)
        context = self._fmt_context(symbol, ctx)
        prompt = f"""
Provide a recommendation for {symbol} in JSON format:
{{
  "action": "BUY" | "HOLD" | "AVOID",
  "conviction": "HIGH" | "MEDIUM" | "LOW",
  "reasoning": "string",
  "risks": "string",
  "one_liner": "string"
}}

DATA:
{context}
"""
        raw_json = self._call(prompt, is_json=True)
        try:
            result = json.loads(raw_json)
        except json.JSONDecodeError:
            result = {"action": "ERROR", "reasoning": "Failed to parse JSON."}
        
        self.memory.store(f"{symbol}_RECOMMEND", result, ttl=3600)
        return result

    def chat(self, symbol: str, question: str) -> str:
        ctx = self._get_context(symbol)
        context = self._fmt_context(symbol, ctx)
        prompt = f"Using ONLY this data: {context}\n\nQuestion: {question}"
        
        result = self._call(prompt)
        ts = datetime.datetime.now(datetime.UTC).strftime('%H%M%S')
        self.memory.store(f"{symbol}_CHAT_{ts}", result, ttl=1800)
        return result