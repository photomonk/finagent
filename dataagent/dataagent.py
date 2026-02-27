import requests
import datetime
import time

class DataAgent:
    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key, memory, ttl=3600):
        self.api_key = api_key
        self.memory = memory
        self.ttl = ttl  # cache time-to-live in seconds

    def fetch_company_overview(self, symbol):
        # 1️⃣ Check memory cache first
        cached = self.memory.retrieve(symbol)
        if cached:
            print("Returning cached data...")
            return cached

        params = {
            "function": "OVERVIEW",
            "symbol": symbol,
            "apikey": self.api_key
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")

        data = response.json()

        # 2️⃣ Handle rate limit message
        if "Note" in data:
            raise Exception("API rate limit reached. Please retry later.")

        if "Symbol" not in data:
            raise Exception(f"Invalid API response for {symbol}")

        # 3️⃣ Normalize numeric fields safely
        def safe_float(value):
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        structured_data = {
            "symbol": data.get("Symbol"),
            "revenue_ttm": safe_float(data.get("RevenueTTM")),
            "market_cap": safe_float(data.get("MarketCapitalization")),
            "pe_ratio": safe_float(data.get("PERatio")),
            "sector": data.get("Sector"),
            "industry": data.get("Industry"),
            "timestamp": str(datetime.datetime.utcnow())
        }

        # 4️⃣ Store in memory layer with TTL
        self.memory.store(symbol, structured_data, ttl=self.ttl)
        

        # 5️⃣ Alpha Vantage rate limit safety (free tier)
        time.sleep(12)

        return structured_data
    
    def fetch_income_statement(self, symbol):
        cache_key = f"{symbol}_INCOME"

        cached = self.memory.retrieve(cache_key)
        if cached:
            print("Returning cached income statement...")
            return cached

        params = {
            "function": "INCOME_STATEMENT",
            "symbol": symbol,
            "apikey": self.api_key
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Income API failed: {str(e)}")

        data = response.json()

        if "Note" in data:
            raise Exception("API rate limit reached.")

        if "annualReports" not in data:
            raise Exception(f"Invalid income statement response for {symbol}")

        def safe_float(v):
            try:
                return float(v)
            except:
                return None

        # Take last 3 years
        reports = data["annualReports"][:3]

        structured = []
        for r in reports:
            structured.append({
                "fiscal_date": r.get("fiscalDateEnding"),
                "revenue": safe_float(r.get("totalRevenue")),
                "gross_profit": safe_float(r.get("grossProfit")),
                "operating_income": safe_float(r.get("operatingIncome")),
                "net_income": safe_float(r.get("netIncome")),
                "ebitda": safe_float(r.get("ebitda")),
            })

        self.memory.store(cache_key, structured, ttl=self.ttl)
        time.sleep(12)

        return structured

    def fetch_balance_sheet(self, symbol):

        cache_key = f"{symbol}_BALANCE"

        cached = self.memory.retrieve(cache_key)
        if cached:
            print("Returning cached balance sheet...")
            return cached

        params = {
            "function": "BALANCE_SHEET",
            "symbol": symbol,
            "apikey": self.api_key
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Balance sheet API failed: {str(e)}")

        data = response.json()

        if "Note" in data:
            raise Exception("API rate limit reached.")

        if "annualReports" not in data:
            raise Exception(f"Invalid balance sheet response for {symbol}")

        def safe_float(v):
            try:
                return float(v)
            except:
                return None

        reports = data["annualReports"][:3]

        structured = []
        for r in reports:
            structured.append({
                "fiscal_date": r.get("fiscalDateEnding"),
                "total_assets": safe_float(r.get("totalAssets")),
                "total_liabilities": safe_float(r.get("totalLiabilities")),
                "total_equity": safe_float(r.get("totalShareholderEquity")),
                "current_assets": safe_float(r.get("totalCurrentAssets")),
                "current_liabilities": safe_float(r.get("totalCurrentLiabilities")),
                "long_term_debt": safe_float(r.get("longTermDebt")),
                "cash": safe_float(r.get("cashAndCashEquivalentsAtCarryingValue")),
            })

        self.memory.store(cache_key, structured, ttl=self.ttl)
        time.sleep(12)

        return structured
    
    def fetch_cash_flow(self, symbol):
        cache_key = f"{symbol}_CASHFLOW"

        cached = self.memory.retrieve(cache_key)
        if cached:
            print("Returning cached cash flow...")
            return cached

        params = {
            "function": "CASH_FLOW",
            "symbol": symbol,
            "apikey": self.api_key
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Cash flow API failed: {str(e)}")

        data = response.json()

        if "Note" in data:
            raise Exception("API rate limit reached.")

        if "annualReports" not in data:
            raise Exception(f"Invalid cash flow response for {symbol}")

        def safe_float(v):
            try:
                return float(v)
            except:
                return None

        reports = data["annualReports"][:3]

        structured = []
        for r in reports:
            structured.append({
                "fiscal_date": r.get("fiscalDateEnding"),
                "operating_cash_flow": safe_float(r.get("operatingCashflow")),
                "capital_expenditure": safe_float(r.get("capitalExpenditures")),
                "free_cash_flow": (
                    safe_float(r.get("operatingCashflow")) -
                    safe_float(r.get("capitalExpenditures"))
                    if safe_float(r.get("operatingCashflow")) and safe_float(r.get("capitalExpenditures"))
                    else None
                )
            })

        self.memory.store(cache_key, structured, ttl=self.ttl)
        time.sleep(12)

        return structured
    