"""
build_investor_cache.py
네이버 모바일 증권 API(https://m.stock.naver.com/api/index/{MARKET}/trend)를 활용하여
2020년부터 최신 거래일까지의 코스피(KOSPI) 및 코스닥(KOSDAQ)의
외국인, 기관, 개인 일별 순매수(단위: 억원) 실데이터를 수집 및 영구 로컬 캐싱합니다.
"""

import os
import time
import requests
import pandas as pd
import concurrent.futures

BASE_DIR = r"d:\AI Investing\03 MarketBalance"
PRICE_CACHE_PATH = os.path.join(BASE_DIR, "data", "index_price_cache.csv")
OUT_CACHE_PATH = os.path.join(BASE_DIR, "data", "krx_investor_daily_cache.csv")

def parse_val(v) -> float:
    if v is None:
        return 0.0
    s = str(v).replace(",", "").replace("+", "").strip()
    try:
        return float(s)
    except:
        return 0.0

def build_investor_cache(start_date: str = "2020-01-01"):
    if not os.path.exists(PRICE_CACHE_PATH):
        print(f"Price cache not found at {PRICE_CACHE_PATH}")
        return

    df_price = pd.read_csv(PRICE_CACHE_PATH)
    all_dates = sorted(df_price[df_price["market"] == "KOSPI"]["date"].unique())
    target_dates = [d for d in all_dates if d >= start_date]

    print(f"Total target dates to fetch: {len(target_dates)} (from {target_dates[0]} to {target_dates[-1]})")

    # 기존 캐시가 있으면 이미 수집된 날짜는 건너뛰기 (Incremental Fetch)
    existing_map = {}
    if os.path.exists(OUT_CACHE_PATH):
        try:
            df_exist = pd.read_csv(OUT_CACHE_PATH)
            for _, r in df_exist.iterrows():
                existing_map[r["date"]] = r.to_dict()
            print(f"Loaded {len(existing_map)} existing cached records.")
        except Exception as e:
            print(f"Could not load existing cache: {e}")

    dates_to_fetch = [d for d in target_dates if d not in existing_map]
    print(f"New dates to fetch: {len(dates_to_fetch)}")

    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=25, pool_maxsize=25, max_retries=2)
    session.mount("https://", adapter)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://m.stock.naver.com/"
    }

    def fetch_date(d_str):
        d_compact = d_str.replace("-", "")
        url_kp = f"https://m.stock.naver.com/api/index/KOSPI/trend?bizdate={d_compact}"
        url_kq = f"https://m.stock.naver.com/api/index/KOSDAQ/trend?bizdate={d_compact}"

        kp_f, kp_i, kp_p = 0.0, 0.0, 0.0
        kq_f, kq_i, kq_p = 0.0, 0.0, 0.0

        try:
            rkp = session.get(url_kp, headers=headers, timeout=6)
            if rkp.status_code == 200:
                jkp = rkp.json()
                kp_f = parse_val(jkp.get("foreignValue"))
                kp_i = parse_val(jkp.get("institutionalValue"))
                kp_p = parse_val(jkp.get("personalValue"))
        except Exception:
            pass

        try:
            rkq = session.get(url_kq, headers=headers, timeout=6)
            if rkq.status_code == 200:
                jkq = rkq.json()
                kq_f = parse_val(jkq.get("foreignValue"))
                kq_i = parse_val(jkq.get("institutionalValue"))
                kq_p = parse_val(jkq.get("personalValue"))
        except Exception:
            pass

        return {
            "date": d_str,
            "kp_foreign_daily": kp_f,
            "kp_inst_daily": kp_i,
            "kp_personal_daily": kp_p,
            "kq_foreign_daily": kq_f,
            "kq_inst_daily": kq_i,
            "kq_personal_daily": kq_p
        }

    t0 = time.time()
    results = []

    if dates_to_fetch:
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            fetched_rows = list(executor.map(fetch_date, dates_to_fetch))
            for item in fetched_rows:
                existing_map[item["date"]] = item
        t1 = time.time()
        print(f"Fetched {len(dates_to_fetch)} dates in {t1 - t0:.2f} seconds.")

    # 전체 데이터 정렬 및 저장
    all_records = [existing_map[d] for d in target_dates if d in existing_map]
    df_out = pd.DataFrame(all_records).sort_values("date").reset_index(drop=True)
    df_out.to_csv(OUT_CACHE_PATH, index=False, encoding="utf-8-sig")
    print(f"Saved {len(df_out)} records to {OUT_CACHE_PATH}")
    print(df_out.tail(5))

if __name__ == "__main__":
    build_investor_cache()
