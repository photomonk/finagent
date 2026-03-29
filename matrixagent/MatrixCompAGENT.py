import datetime

class MetricsAgent:

    def __init__(self, memory):
        self.memory = memory

    def compute_metrics(self, symbol):

        metrics_key = f"{symbol}_METRICS"

        # 1️⃣ Check if metrics already computed
        cached_metrics = self.memory.retrieve(metrics_key)
        if cached_metrics:
            print("Returning cached metrics...")
            return cached_metrics

        # 2️⃣ Retrieve financial statements from memory
        income_data = self.memory.retrieve(f"{symbol}_INCOME")
        balance_data = self.memory.retrieve(f"{symbol}_BALANCE")
        cashflow_data = self.memory.retrieve(f"{symbol}_CASHFLOW")

        if not income_data or not balance_data or not cashflow_data:
            raise ValueError("Financial data missing in memory.")

        income_latest = income_data[0]
        balance_latest = balance_data[0]
        cashflow_latest = cashflow_data[0]

        income_prev = income_data[1] if len(income_data) > 1 else None
        cashflow_prev = cashflow_data[1] if len(cashflow_data) > 1 else None

        def safe_div(n, d):
            if n is None or d in (None, 0):
                return None
            return n / d

        def growth(curr, prev):
            if curr is None or prev in (None, 0):
                return None
            return (curr - prev) / prev

        # 🔹 Core Metrics
        profit_margin = safe_div(
            income_latest["net_income"],
            income_latest["revenue"]
        )

        roe = safe_div(
            income_latest["net_income"],
            balance_latest["total_equity"]
        )

        debt_to_equity = safe_div(
            balance_latest["total_liabilities"],
            balance_latest["total_equity"]
        )

        current_ratio = safe_div(
            balance_latest["current_assets"],
            balance_latest["current_liabilities"]
        )

        free_cash_flow = cashflow_latest["free_cash_flow"]

        revenue_growth = growth(
            income_latest["revenue"],
            income_prev["revenue"] if income_prev else None
        )

        fcf_growth = growth(
            cashflow_latest["free_cash_flow"],
            cashflow_prev["free_cash_flow"] if cashflow_prev else None
        )
        OPERATING_MARGIN = safe_div(
            income_latest["operating_income"],
            income_latest["revenue"]
        )
        ASSET_TURNOVER = safe_div(
            income_latest["revenue"],
            balance_latest["total_assets"]
        )
        


        metrics = {
            "symbol": symbol,
            "fiscal_year": income_latest["fiscal_date"],
            "profit_margin": profit_margin,
            "roe": roe,
            "debt_to_equity": debt_to_equity,
            "current_ratio": current_ratio,
            "revenue_growth": revenue_growth,
            "free_cash_flow": free_cash_flow,
            "fcf_growth": fcf_growth,
            "operating_margin": OPERATING_MARGIN,
            "asset_turnover": ASSET_TURNOVER,
            
            "generated_at": str(datetime.datetime.utcnow())
        }

        # 3️⃣ Store computed metrics in memory
        self.memory.store(metrics_key, metrics, ttl=3600)

        return metrics
    