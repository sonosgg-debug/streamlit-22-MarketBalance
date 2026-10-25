"""
build_index_price_cache.py
KOSPI 및 KOSDAQ 지수 시세 로컬 캐시 생성 (Zero Network Startup 보장)
"""
import os
import requests
import xml.etree.ElementTree as ET
import pandas as pd

def build_price_cache():
    markets = ["KOSPI", "KOSDAQ"]
    all_dfs = []

    for m in markets:
        print(f"Fetching {m} from Naver fchart...")
        url = f"https://fchart.stock.naver.com/sise.nhn?symbol={m}&timeframe=day&count=3000&requestType=0"
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5.0)
            root = ET.fromstring(r.text)
            records = []
            for item in root.findall(".//item"):
                data_str = item.attrib.get("data", "")
                parts = data_str.split("|")
                if len(parts) >= 6:
                    raw_d = parts[0]
                    d_str = f"{raw_d[:4]}-{raw_d[4:6]}-{raw_d[6:8]}"
                    records.append({
                        "date": d_str,
                        "open": float(parts[1]),
                        "high": float(parts[2]),
                        "low": float(parts[3]),
                        "close": float(parts[4]),
                        "volume": float(parts[5]),
                        "market": m
                    })
            df = pd.DataFrame(records)
            print(f"{m} fetched: {len(df)} rows")
            all_dfs.append(df)
        except Exception as e:
            print(f"Failed to fetch {m}: {e}")

    if all_dfs:
        df_total = pd.concat(all_dfs, ignore_index=True)
        df_total["date"] = pd.to_datetime(df_total["date"]).dt.strftime("%Y-%m-%d")
        df_total = df_total.sort_values(["market", "date"]).reset_index(drop=True)
        out_path = r"d:\AI Investing\03 MarketBalance\data\index_price_cache.csv"
        df_total.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"Saved {len(df_total)} rows to {out_path}")

if __name__ == "__main__":
    build_price_cache()
