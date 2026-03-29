from dataagent.dataagent import DataAgent
from memory.memorylayer import MemoryLayer
from matrixagent.MatrixCompAGENT import MetricsAgent
from llmagent.LLMAgentComp import LLMAgent
from scoreengine.scoreEngine import score_company,print_score_report
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
    if not memory.check_key(f"{user_input}_OVERVIEW"):
        overview = data_agent.fetch_company_overview(user_input)
        memory.store(f"{user_input}_OVERVIEW", overview)

    if not memory.check_key(f"{user_input}_INCOME"):
        income = data_agent.fetch_income_statement(user_input)
        memory.store(f"{user_input}_INCOME", income)

    if not memory.check_key(f"{user_input}_BALANCE"):
        balance = data_agent.fetch_balance_sheet(user_input)
        memory.store(f"{user_input}_BALANCE", balance)

    if not memory.check_key(f"{user_input}_CASHFLOW"):
        cashflow = data_agent.fetch_cash_flow(user_input)
        memory.store(f"{user_input}_CASHFLOW", cashflow)




    metrics = matrix_agent.compute_metrics(user_input)
    print(metrics)
    print(metrics["generated_at"])

    SCORE=score_company(user_input,memory)
    print_score_report(SCORE)
    



    from llmagent import LLMAgentComp
    api_key = os.getenv("gemini_API-Key")

    llm = LLMAgent(api_key, memory)

    # after scoring is done:

    # plain English verdict
    text = llm.verdict("AAPL")
    print(text)

    # buy / hold / avoid
    rec = llm.recommend("AAPL")
    print(rec)

    # compare two stocks
    # 
    # print(llm.compare("AAPL", "MSFT"))

    # follow-up question
    print(llm.chat("AAPL", "Why is the safety score low?"))


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



