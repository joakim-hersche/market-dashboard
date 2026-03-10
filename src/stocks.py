import pandas as pd
import requests

def get_sp500_stocks():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    
    # Mimic a browser request to avoid 403 block
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    
    table = pd.read_html(response.text)[0]
    
    stocks = {}
    for _, row in table.iterrows():
        ticker = row["Symbol"]
        name = row["Security"]
        stocks[f"{name} ({ticker})"] = ticker
    
    return stocks