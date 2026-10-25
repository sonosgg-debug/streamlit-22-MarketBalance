import os
import sys
import pandas as pd
import datetime

# Load KRX credentials
api_key_path = r"D:\AI Investing\00 API Key\KRX ID&PW.txt"
if os.path.exists(api_key_path):
    with open(api_key_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("ID :") or line.startswith("ID:"):
                os.environ["KRX_ID"] = line.split(":", 1)[1].strip()
            elif line.startswith("PW :") or line.startswith("PW:"):
                os.environ["KRX_PW"] = line.split(":", 1)[1].strip()

import pykrx.stock as stock

def build_fundamentals():
    print("Collecting KOSPI fundamentals (2020-01-01 to 2026-10-25)...")
    df_kospi = stock.get_index_fundamental("20200101", "20261025", "1001")
    df_kospi = df_kospi.reset_index()
    # rename columns
    df_kospi.columns = ["date", "close", "change_pct", "per", "pbr", "div_yield"]
    df_kospi["market"] = "KOSPI"
    print(f"KOSPI done: {len(df_kospi)} rows")

    print("Collecting KOSDAQ fundamentals (2020-01-01 to 2026-10-25)...")
    df_kosdaq = stock.get_index_fundamental("20200101", "20261025", "2001")
    df_kosdaq = df_kosdaq.reset_index()
    df_kosdaq.columns = ["date", "close", "change_pct", "per", "pbr", "div_yield"]
    df_kosdaq["market"] = "KOSDAQ"
    print(f"KOSDAQ done: {len(df_kosdaq)} rows")

    df_all = pd.concat([df_kospi, df_kosdaq], ignore_index=True)
    df_all["date"] = pd.to_datetime(df_all["date"]).dt.strftime("%Y-%m-%d")
    out_path = r"d:\AI Investing\03 MarketBalance\data\krx_fundamentals_cache.csv"
    df_all.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"Saved fundamentals to {out_path} ({len(df_all)} total rows)")

if __name__ == "__main__":
    build_fundamentals()
