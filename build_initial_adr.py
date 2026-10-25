import os
import sys
import time
import datetime
import pandas as pd
import concurrent.futures

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

def build_adr():
    fund_path = r"d:\AI Investing\03 MarketBalance\data\krx_fundamentals_cache.csv"
    if not os.path.exists(fund_path):
        print("Fundamentals cache not found!")
        return

    df_fund = pd.read_csv(fund_path)
    # Get distinct trading dates sorted
    all_dates = sorted(list(df_fund["date"].unique()))
    print(f"Total available trading days: {len(all_dates)}")

    # We will fetch the last 350 trading days (approx 1.5 years)
    target_dates = all_dates[-350:]
    print(f"Targeting {len(target_dates)} dates from {target_dates[0]} to {target_dates[-1]}")

    adr_path = r"d:\AI Investing\03 MarketBalance\data\krx_adr_history.csv"
    existing_records = {}
    if os.path.exists(adr_path):
        try:
            df_exist = pd.read_csv(adr_path)
            for _, row in df_exist.iterrows():
                existing_records[str(row["date"])] = {
                    "date": str(row["date"]),
                    "kospi_adv": int(row["kospi_adv"]),
                    "kospi_dec": int(row["kospi_dec"]),
                    "kosdaq_adv": int(row["kosdaq_adv"]),
                    "kosdaq_dec": int(row["kosdaq_dec"]),
                }
            print(f"Loaded {len(existing_records)} existing ADR records")
        except Exception as e:
            print(f"Error reading existing ADR file: {e}")

    dates_to_fetch = [d for d in target_dates if d not in existing_records]
    print(f"Dates to fetch: {len(dates_to_fetch)}")

    def fetch_one(d_str):
        d_nodash = d_str.replace("-", "")
        for attempt in range(2):
            try:
                time.sleep(0.05)
                df_kp = stock.get_market_price_change_by_ticker(d_nodash, d_nodash, market="KOSPI")
                adv_kp = len(df_kp[df_kp["등락률"] > 0])
                dec_kp = len(df_kp[df_kp["등락률"] < 0])

                df_kq = stock.get_market_price_change_by_ticker(d_nodash, d_nodash, market="KOSDAQ")
                adv_kq = len(df_kq[df_kq["등락률"] > 0])
                dec_kq = len(df_kq[df_kq["등락률"] < 0])

                if adv_kp > 0 or dec_kp > 0:
                    return {
                        "date": d_str,
                        "kospi_adv": adv_kp,
                        "kospi_dec": dec_kp,
                        "kosdaq_adv": adv_kq,
                        "kosdaq_dec": dec_kq,
                    }
            except Exception as ex:
                time.sleep(0.3)
        return None

    if dates_to_fetch:
        print("Starting parallel fetch (max_workers=4)...")
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_date = {executor.submit(fetch_one, d): d for d in dates_to_fetch}
            completed = 0
            for future in concurrent.futures.as_completed(future_to_date):
                completed += 1
                res = future.result()
                if res:
                    results.append(res)
                if completed % 50 == 0 or completed == len(dates_to_fetch):
                    print(f"Progress: {completed}/{len(dates_to_fetch)} (collected {len(results)})")

        for r in results:
            existing_records[r["date"]] = r

    df_out = pd.DataFrame(list(existing_records.values()))
    if not df_out.empty:
        df_out = df_out.sort_values("date").reset_index(drop=True)
        df_out.to_csv(adr_path, index=False, encoding="utf-8-sig")
        print(f"Successfully saved {len(df_out)} ADR records to {adr_path}")

if __name__ == "__main__":
    build_adr()
