"""
data_loader.py
Market Balance 대시보드를 위한 데이터 수집, 캐싱, 지표 계산 엔진.
- 00 App_AI_Template 공통 가이드 (01~07) 엄격 준수
- Zero Network Startup: 로컬 캐시 최우선 반환
- Multi-tier Fallback: Naver fchart -> yfinance -> fdr
- 防御的 API 설계: kwargs 수용 및 캐시 무결성
"""

import os
import sys
import io
import time
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np
import requests

from config import (
    KST,
    MARKET_KEY_MAP,
    NAVER_INDEX_MAP,
    YFINANCE_INDEX_MAP,
    KRX_INDEX_CODE_MAP,
    FUNDAMENTALS_CACHE_PATH,
    ADR_HISTORY_PATH,
    PRICE_CACHE_PATH,
    EXTENDED_INDICATORS_PATH,
    DATA_DIR
)

# KRX 인증 환경변수 로딩
def ensure_krx_auth():
    if not os.getenv("KRX_ID") or not os.getenv("KRX_PW"):
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        api_key_path = os.path.join(parent_dir, "00 API Key", "KRX ID&PW.txt")
        if os.path.exists(api_key_path):
            try:
                with open(api_key_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("ID :") or line.startswith("ID:"):
                            os.environ["KRX_ID"] = line.split(":", 1)[1].strip()
                        elif line.startswith("PW :") or line.startswith("PW:"):
                            os.environ["KRX_PW"] = line.split(":", 1)[1].strip()
            except Exception:
                pass

ensure_krx_auth()

# pykrx 안전 로딩
try:
    from pykrx import stock
    HAS_PYKRX = True
except Exception:
    stock = None
    HAS_PYKRX = False


def get_latest_expected_trading_day() -> str:
    """
    [가이드 04] KST 기준 최신 기대 거래일 반환
    - 평일 15:45 이후에만 당일 종가 채택
    - 새벽(00:00~08:59), 주말, 장전에는 직전 영업일로 안전 역추적
    """
    now_kst = datetime.now(KST)
    today = now_kst.date()

    # 평일이고 15:45 이후이면 오늘
    if now_kst.weekday() < 5 and (now_kst.hour > 15 or (now_kst.hour == 15 and now_kst.minute >= 45)):
        return today.strftime("%Y-%m-%d")

    # 장전, 새벽, 주말: 직전 평일로 역추적
    d = today - timedelta(days=1)
    while d.weekday() >= 5:  # 토, 일 건너뜀
        d -= timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def fetch_index_price_naver(market: str = "KOSPI", count: int = 4000) -> pd.DataFrame:
    """
    [가이드 06] 1순위: 네이버 금융 공식 차트 API를 통한 지수 시세 수집
    """
    symbol = NAVER_INDEX_MAP.get(market, "KOSPI")
    url = f"https://fchart.stock.naver.com/sise.nhn?symbol={symbol}&timeframe=day&count={count}&requestType=0"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=5.0)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    items = root.findall(".//item")
    if not items:
        return pd.DataFrame()

    records = []
    for item in items:
        data_str = item.attrib.get("data", "")
        parts = data_str.split("|")
        if len(parts) >= 6:
            raw_date = parts[0]  # YYYYMMDD
            date_fmt = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
            records.append({
                "date": date_fmt,
                "open": float(parts[1]),
                "high": float(parts[2]),
                "low": float(parts[3]),
                "close": float(parts[4]),
                "volume": float(parts[5]),
                "market": market
            })

    df = pd.DataFrame(records)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        df = df.sort_values("date").reset_index(drop=True)
    return df


def fetch_index_price_fallback(market: str = "KOSPI") -> pd.DataFrame:
    """
    [가이드 06] 2순위/3순위: yfinance 또는 fdr 폴백
    """
    # 2순위 yfinance
    try:
        import yfinance as yf
        ticker = YFINANCE_INDEX_MAP.get(market, "^KS11")
        df_yf = yf.download(ticker, period="5y", progress=False)
        if df_yf is not None and not df_yf.empty:
            df_yf = df_yf.reset_index()
            # MultiIndex columns 처리
            if isinstance(df_yf.columns, pd.MultiIndex):
                df_yf.columns = [c[0] for c in df_yf.columns]
            df_yf = df_yf.rename(columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume"
            })
            df_yf["date"] = pd.to_datetime(df_yf["date"]).dt.strftime("%Y-%m-%d")
            df_yf["market"] = market
            return df_yf[["date", "open", "high", "low", "close", "volume", "market"]]
    except Exception:
        pass

    # 3순위 FinanceDataReader
    try:
        import FinanceDataReader as fdr
        code = "KS11" if market == "KOSPI" else "KQ11"
        df_fdr = fdr.DataReader(code, "2020-01-01")
        if df_fdr is not None and not df_fdr.empty:
            df_fdr = df_fdr.reset_index().rename(columns={
                "Date": "date", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"
            })
            df_fdr["date"] = pd.to_datetime(df_fdr["date"]).dt.strftime("%Y-%m-%d")
            df_fdr["market"] = market
            return df_fdr[["date", "open", "high", "low", "close", "volume", "market"]]
    except Exception:
        pass

    return pd.DataFrame()


def get_index_price(market: str = "KOSPI", force_refresh: bool = False, **kwargs) -> pd.DataFrame:
    """
    [가이드 05, 06] KOSPI 또는 KOSDAQ의 주가지수 시계열 수집
    - Zero Network Startup: 로컬 캐시(PRICE_CACHE_PATH) 최우선 반환
    - 최신일 갱신 필요 시 네이버 fchart -> yfinance -> fdr 폴백
    """
    df_cache = None
    if os.path.exists(PRICE_CACHE_PATH):
        try:
            df_all = pd.read_csv(PRICE_CACHE_PATH)
            df_all["date"] = pd.to_datetime(df_all["date"]).dt.strftime("%Y-%m-%d")
            df_cache = df_all[df_all["market"] == market].copy().sort_values("date").reset_index(drop=True)
        except Exception:
            df_cache = None

    expected_day = get_latest_expected_trading_day()

    # 캐시가 없거나 최신일이 부족하거나 강제 갱신 요청 시 외부 API 시도
    if force_refresh or df_cache is None or df_cache.empty or (df_cache["date"].iloc[-1] < expected_day):
        try:
            df_fresh = fetch_index_price_naver(market=market)
            if df_fresh is not None and not df_fresh.empty and len(df_fresh) >= 50:
                # 로컬 캐시 갱신
                if df_cache is not None and not df_cache.empty:
                    combined = pd.concat([df_cache, df_fresh], ignore_index=True)
                    combined = combined.drop_duplicates(subset=["date", "market"], keep="last")
                    combined = combined.sort_values(["market", "date"]).reset_index(drop=True)
                    try:
                        # 전체 시장 캐시와 병합 저장
                        df_other = df_all[df_all["market"] != market] if (df_cache is not None and os.path.exists(PRICE_CACHE_PATH)) else pd.DataFrame()
                        pd.concat([df_other, combined], ignore_index=True).to_csv(PRICE_CACHE_PATH, index=False, encoding="utf-8-sig")
                    except Exception:
                        pass
                    return combined
                else:
                    return df_fresh
        except Exception as e:
            # 네트워크 오류 시 조용히 로컬 캐시로 폴백
            pass

    if df_cache is not None and not df_cache.empty:
        return df_cache

    return fetch_index_price_fallback(market=market)


def get_fundamentals_data(market: str = "KOSPI", force_refresh: bool = False, **kwargs) -> pd.DataFrame:
    """
    [가이드 05] 로컬 캐시 최우선 로드 후 필요 시 최신 거래일 증분 동기화
    """
    df_cache = None
    if os.path.exists(FUNDAMENTALS_CACHE_PATH):
        try:
            df_cache = pd.read_csv(FUNDAMENTALS_CACHE_PATH)
            df_cache["date"] = pd.to_datetime(df_cache["date"]).dt.strftime("%Y-%m-%d")
        except Exception:
            df_cache = None

    expected_day = get_latest_expected_trading_day()

    # 강제 갱신이거나 캐시가 비어있거나 최신일이 부족할 때 증분 수집
    if force_refresh or df_cache is None or df_cache.empty:
        if HAS_PYKRX and stock is not None:
            try:
                ensure_krx_auth()
                m_code = KRX_INDEX_CODE_MAP.get(market, "1001")
                # 최신 30일치 수집
                start_q = (datetime.now(KST) - timedelta(days=60)).strftime("%Y%m%d")
                end_q = datetime.now(KST).strftime("%Y%m%d")
                df_fresh = stock.get_index_fundamental(start_q, end_q, m_code)
                if df_fresh is not None and not df_fresh.empty:
                    df_fresh = df_fresh.reset_index()
                    df_fresh.columns = ["date", "close", "change_pct", "per", "pbr", "div_yield"]
                    df_fresh["market"] = market
                    df_fresh["date"] = pd.to_datetime(df_fresh["date"]).dt.strftime("%Y-%m-%d")

                    if df_cache is not None and not df_cache.empty:
                        # 병합 및 중복 제거
                        combined = pd.concat([df_cache, df_fresh], ignore_index=True)
                        combined = combined.drop_duplicates(subset=["date", "market"], keep="last")
                        combined = combined.sort_values(["market", "date"]).reset_index(drop=True)
                        combined.to_csv(FUNDAMENTALS_CACHE_PATH, index=False, encoding="utf-8-sig")
                        df_cache = combined
                    else:
                        df_fresh.to_csv(FUNDAMENTALS_CACHE_PATH, index=False, encoding="utf-8-sig")
                        df_cache = df_fresh
            except Exception as e:
                print(f"Incremental KRX fundamentals sync failed: {e}", file=sys.stderr)

    if df_cache is not None and not df_cache.empty:
        df_filtered = df_cache[df_cache["market"] == market].copy()
        df_filtered = df_filtered.sort_values("date").reset_index(drop=True)
        return df_filtered

    return pd.DataFrame()


def get_live_naver_adr_counts(market: str = "KOSPI") -> tuple:
    """
    네이버 모바일 통합 API에서 실시간/당일 상승/하락 종목 수를 가져옵니다.
    반환: (rise_count, fall_count)
    """
    symbol = NAVER_INDEX_MAP.get(market, "KOSPI")
    url = f"https://m.stock.naver.com/api/index/{symbol}/integration"
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            up_down = data.get("upDownStockInfo", {})
            rise = int(str(up_down.get("riseCount", "0")).replace(",", "")) + int(str(up_down.get("upperCount", "0")).replace(",", ""))
            fall = int(str(up_down.get("fallCount", "0")).replace(",", "")) + int(str(up_down.get("lowerCount", "0")).replace(",", ""))
            return rise, fall
    except Exception:
        pass
    return 0, 0


def get_adr_history(market: str = "KOSPI", force_refresh: bool = False, **kwargs) -> pd.DataFrame:
    """
    [가이드 05] 로컬 ADR 캐시 최우선 로드 후 필요 시 당일 실시간 수치 동기화
    """
    df_adr = None
    if os.path.exists(ADR_HISTORY_PATH):
        try:
            df_adr = pd.read_csv(ADR_HISTORY_PATH)
            df_adr["date"] = pd.to_datetime(df_adr["date"]).dt.strftime("%Y-%m-%d")
        except Exception:
            df_adr = None

    expected_day = get_latest_expected_trading_day()

    # 당일 데이터 보충 확인
    if df_adr is not None and not df_adr.empty:
        existing_dates = set(df_adr["date"].values)
        if (expected_day not in existing_dates) or force_refresh:
            # 네이버 실시간 또는 pykrx로 당일 수치 보충
            rise_kp, fall_kp = get_live_naver_adr_counts("KOSPI")
            rise_kq, fall_kq = get_live_naver_adr_counts("KOSDAQ")
            if (rise_kp > 0 or fall_kp > 0) or (rise_kq > 0 or fall_kq > 0):
                new_row = {
                    "date": expected_day,
                    "kospi_adv": rise_kp,
                    "kospi_dec": fall_kp,
                    "kosdaq_adv": rise_kq,
                    "kosdaq_dec": fall_kq,
                }
                # 업데이트 또는 추가
                if expected_day in existing_dates:
                    idx = df_adr[df_adr["date"] == expected_day].index
                    for k, v in new_row.items():
                        df_adr.loc[idx, k] = v
                else:
                    df_adr = pd.concat([df_adr, pd.DataFrame([new_row])], ignore_index=True)
                
                df_adr = df_adr.sort_values("date").reset_index(drop=True)
                try:
                    df_adr.to_csv(ADR_HISTORY_PATH, index=False, encoding="utf-8-sig")
                except Exception:
                    pass

    return df_adr if df_adr is not None else pd.DataFrame()


def calculate_rsi(series: pd.Series, period: int = 20) -> pd.Series:
    """
    Wilder's Smoothing 방식을 적용한 정석 RSI(20) 계산.
    """
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # 지수이동평균 (Wilder's alpha = 1 / period)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    # loss가 0인 경우 100 처리, gain이 0인 경우 0 처리
    rsi = rsi.where(avg_loss != 0, 100.0)
    rsi = rsi.where(avg_gain != 0, 0.0)
    return rsi.round(2)


def calculate_adr_metrics(df_adr: pd.DataFrame, market: str = "KOSPI", period: int = 14) -> pd.DataFrame:
    """
    일자별 등락 종목 수 기반으로 ADR(1) 및 ADR(14) 계산:
    - ADR(1): 당일 상승종목수 / 당일 하락종목수 * 100
    - ADR(14): 최근 14일간 상승종목수 합계 / 최근 14일간 하락종목수 합계 * 100
    """
    if df_adr.empty:
        return pd.DataFrame()

    prefix = "kospi" if market == "KOSPI" else "kosdaq"
    adv_col = f"{prefix}_adv"
    dec_col = f"{prefix}_dec"

    if adv_col not in df_adr.columns or dec_col not in df_adr.columns:
        return pd.DataFrame()

    res = df_adr[["date", adv_col, dec_col]].copy()
    res = res.rename(columns={adv_col: "adv", dec_col: "dec"})
    res = res.sort_values("date").reset_index(drop=True)

    # ADR(1) = 당일 상승 / 당일 하락 * 100
    res["adr_1"] = np.where(res["dec"] > 0, (res["adv"] / res["dec"]) * 100.0, 100.0)
    res["adr_1"] = res["adr_1"].round(2)

    # ADR(14) = 14일 누적 상승 / 14일 누적 하락 * 100
    rolling_adv = res["adv"].rolling(window=period, min_periods=max(2, period // 2)).sum()
    rolling_dec = res["dec"].rolling(window=period, min_periods=max(2, period // 2)).sum()

    res["adr_14"] = np.where(rolling_dec > 0, (rolling_adv / rolling_dec) * 100.0, 100.0)
    res["adr_14"] = res["adr_14"].round(2)

    return res[["date", "adv", "dec", "adr_1", "adr_14"]]


def parse_market_key(market_choice: str) -> str:
    """시장 문자열에서 'KOSPI' 또는 'KOSDAQ' 키를 안전하게 추출합니다."""
    if not market_choice:
        return "KOSPI"
    s = str(market_choice).upper()
    if "KOSDAQ" in s or "코스닥" in s:
        return "KOSDAQ"
    return "KOSPI"


def get_extended_indicators(market: str = "KOSPI", **kwargs) -> pd.DataFrame:
    """
    [가이드 05] 고객예탁금/신용잔고, VKOSPI, 외인/기관 순매수, 200일선 상회 비율 로드
    """
    if not os.path.exists(EXTENDED_INDICATORS_PATH):
        return pd.DataFrame()

    try:
        df_ext = pd.read_csv(EXTENDED_INDICATORS_PATH)
        df_ext["date"] = pd.to_datetime(df_ext["date"]).dt.strftime("%Y-%m-%d")

        # 시장별 필터링 컬럼 매핑
        is_kp = (market == "KOSPI")
        for_daily_col = "kp_foreign_daily" if is_kp else "kq_foreign_daily"
        inst_daily_col = "kp_inst_daily" if is_kp else "kq_inst_daily"
        pers_daily_col = "kp_personal_daily" if is_kp else "kq_personal_daily"
        for_col = "kp_foreign_cum" if is_kp else "kq_foreign_cum"
        inst_col = "kp_inst_cum" if is_kp else "kq_inst_cum"
        ma200_col = "kp_above_200ma" if is_kp else "kq_above_200ma"

        res = pd.DataFrame()
        res["date"] = df_ext["date"]
        # 조원 환산 (1조원 = 10,000억원)
        res["deposit_jo"] = (df_ext["deposit_eok"] / 10000.0).round(2)
        res["credit_jo"] = (df_ext["credit_eok"] / 10000.0).round(2)
        res["credit_ratio"] = df_ext["credit_ratio"].round(2)
        res["vkospi"] = df_ext["vkospi"].round(2)
        res["foreign_daily_eok"] = df_ext[for_daily_col].round(1) if for_daily_col in df_ext.columns else 0.0
        res["inst_daily_eok"] = df_ext[inst_daily_col].round(1) if inst_daily_col in df_ext.columns else 0.0
        res["personal_daily_eok"] = df_ext[pers_daily_col].round(1) if pers_daily_col in df_ext.columns else 0.0
        res["foreign_cum_jo"] = (df_ext[for_col] / 10000.0).round(2)
        res["inst_cum_jo"] = (df_ext[inst_col] / 10000.0).round(2)
        res["above_200ma"] = df_ext[ma200_col].round(1)

        return res
    except Exception as e:
        print(f"Error loading extended indicators: {e}", file=sys.stderr)
        return pd.DataFrame()


def get_market_balance_dataset(market_choice: str = "코스피 (KOSPI)", force_refresh: bool = False, **kwargs) -> pd.DataFrame:
    """
    대시보드 통합 데이터셋을 생성합니다.
    - 지수 종가 (Close, Open, High, Low)
    - 펀더멘털 지표 (PER, PBR)
    - 기술적 모멘텀 지표 (RSI 20)
    - 시장 심리/넓이 지표 (ADR 14, ADR 1)
    - 수급/변동성/건전성 지표 (예탁금, 신용잔고, VKOSPI, 외인/기관 순매수, 200일선 상회)
    """
    market = parse_market_key(market_choice)

    # 1. 지수 시세 수집
    df_price = get_index_price(market=market, force_refresh=force_refresh)
    if df_price.empty:
        return pd.DataFrame()

    # 2. RSI(20) 및 이동평균선(MA 5, 20, 60, 120) 계산 (전체 시계열 기준 선행 계산)
    df_price["rsi_20"] = calculate_rsi(df_price["close"], period=20)
    df_price["ma5"] = df_price["close"].rolling(window=5, min_periods=1).mean().round(2)
    df_price["ma20"] = df_price["close"].rolling(window=20, min_periods=1).mean().round(2)
    df_price["ma60"] = df_price["close"].rolling(window=60, min_periods=1).mean().round(2)
    df_price["ma120"] = df_price["close"].rolling(window=120, min_periods=1).mean().round(2)

    # 3. PER, PBR 펀더멘털 병합
    df_fund = get_fundamentals_data(market=market, force_refresh=force_refresh)
    if not df_fund.empty:
        df_fund_sub = df_fund[["date", "per", "pbr", "div_yield"]].copy()
        df_merged = pd.merge(df_price, df_fund_sub, on="date", how="left")
    else:
        df_merged = df_price.copy()
        df_merged["per"] = np.nan
        df_merged["pbr"] = np.nan
        df_merged["div_yield"] = np.nan

    # 4. ADR(14) 및 ADR(1) 병합
    df_adr = get_adr_history(market=market, force_refresh=force_refresh)
    if not df_adr.empty:
        df_adr_calc = calculate_adr_metrics(df_adr, market=market, period=14)
        if not df_adr_calc.empty:
            df_merged = pd.merge(df_merged, df_adr_calc, on="date", how="left")
        else:
            df_merged["adr_1"] = np.nan
            df_merged["adr_14"] = np.nan
    else:
        df_merged["adr_1"] = np.nan
        df_merged["adr_14"] = np.nan

    # 5. 확장 4대 지표 병합 (예탁금, 신용잔고, VKOSPI, 외인/기관 누적순매수, 200일선 상회)
    df_ext = get_extended_indicators(market=market)
    if not df_ext.empty:
        df_merged = pd.merge(df_merged, df_ext, on="date", how="left")
    
    # 6. 모든 확장 지표 컬럼 누락 방지 및 방어적 보장
    ext_cols = [
        "deposit_jo", "credit_jo", "credit_ratio", "vkospi",
        "foreign_daily_eok", "inst_daily_eok", "personal_daily_eok",
        "foreign_cum_jo", "inst_cum_jo", "above_200ma"
    ]
    for c in ext_cols:
        if c not in df_merged.columns:
            df_merged[c] = np.nan

    df_merged = df_merged.sort_values("date").reset_index(drop=True)
    return df_merged
