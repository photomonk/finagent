from dataagent.dataagent import DataAgent
from memory.memorylayer import MemoryLayer
from matrixagent.MatrixCompAGENT import MetricsAgent
import pandas as pd

from dotenv import load_dotenv
import os

load_dotenv()

if __name__ == "__main__":
    print("good")
    memory = MemoryLayer(os.getenv("mongo_uri"), os.getenv("mongo_db_name"))
    matrix_agent = MetricsAgent(memory=memory)

    data_agent = DataAgent(api_key=os.getenv("Alpha_vantage_API-Key"), memory=memory)

    user_input = input("Enter a stock symbol: ")
    metrics = matrix_agent.compute_metrics(user_input)
    print(metrics)

    



# Read symbols from CSV file without headers
# symbols_df = pd.read_csv("companies_symbol.txt", header=None, names=["symbol"])

# for symbol in symbols_df['symbol']:
#     print(symbol)
#     overview = data_agent.fetch_company_overview(symbol)
#     income = data_agent.fetch_income_statement(symbol)
#     balance = data_agent.fetch_balance_sheet(symbol)
#     cashflow = data_agent.fetch_cash_flow(symbol)
    
#     # Store fetched data in memory
#     memory.store(f"{symbol}_OVERVIEW", overview)
#     memory.store(f"{symbol}_INCOME", income)
#     memory.store(f"{symbol}_BALANCE", balance)
#     memory.store(f"{symbol}_CASHFLOW", cashflow)
    
#     # Compute and store metrics
#     metrics = matrix_agent.compute_metrics(symbol)
#     memory.store(f"{symbol}_METRICS", metrics)


#     print(balance)
#     print(cashflow)
#     print(overview)
#     print(income)

#     print(metrics)



