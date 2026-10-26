"""
app.py
Market Balance 웹 애플리케이션 엔트리포인트.
- "00 App_AI_Template" 공통 표준 규칙 (01~07) 100% 엄격 준수
- 왼쪽 사이드바: 시장 선택, 지표 선택, 빠른 기간 선택, 캘린더 조회 기간, Update / 조회 버튼
- 오른쪽 메인 화면: 메인 타이틀, 서브 타이틀, KPI 상태 요약, 고대비 합성 차트, 데이터 테이블 및 다운로드
"""

import os
import sys
import io
import datetime
from datetime import date, timedelta
import importlib
import pandas as pd
import numpy as np
from PIL import Image
import streamlit as st

# [가이드 01] 페이지 기본 설정 (스크립트 최상단 의무 선언)
# 브라우저 탭 파비콘: 폴더 내 favicon.png 적용
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FAVICON_PATH = os.path.join(BASE_DIR, "favicon.png")
try:
    if os.path.exists(FAVICON_PATH):
        PAGE_ICON = Image.open(FAVICON_PATH)
    else:
        PAGE_ICON = "📈"
except Exception:
    PAGE_ICON = "📈"

st.set_page_config(
    page_title="Market Balance",
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# [가이드 05] 보조 모듈 강제 리로드 의무화 (Zero Stale Module Freezing)
import config
import data_loader
import chart_builder

importlib.reload(config)
importlib.reload(data_loader)
importlib.reload(chart_builder)

from config import (
    KST,
    APP_TITLE,
    MAIN_TITLE,
    SUB_TITLE,
    DISCLAIMER_TEXT,
    MARKET_OPTIONS,
    DEFAULT_MARKET,
    INDICATOR_OPTIONS,
    DEFAULT_INDICATOR,
    PERIOD_PRESETS,
    DEFAULT_PERIOD,
    INDICATOR_META,
    STANDARD_CHART_THEME
)
from data_loader import (
    get_latest_expected_trading_day,
    get_market_balance_dataset
)
from chart_builder import create_market_balance_chart

# ==============================================================================
# 1. [가이드 01, 02] 공통 CSS 테마 주입 (다크 테마, 사이드바, 다운로드 버튼 규격)
# ==============================================================================
st.markdown(
    """
    <style>
    /* 상단 고정 헤더 배경 투명화 */
    header[data-testid="stHeader"] {
        background: transparent !important;
    }

    /* 화면 상단 패딩 표준화 (2.0rem) */
    .main .block-container,
    [data-testid="stMainBlockContainer"] {
        padding-top: 2.0rem !important;
        padding-bottom: 3.5rem !important;
        max-width: 100% !important;
    }

    /* 사이드바 다크 네이비 테마 & 테두리 */
    section[data-testid="stSidebar"], [data-testid="stSidebar"] {
        background-color: #1e293b !important;
        border-right: 1px solid #334155 !important;
    }
    
    /* 사이드바 텍스트 Pure White 강제 */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #f8fafc !important;
        -webkit-text-fill-color: #f8fafc !important;
    }

    /* 사이드바 접기/열기 버튼 시인성 보강 */
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="stSidebarCollapsedControl"] button {
        background-color: #1e293b !important;
        border: 1.5px solid #38bdf8 !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4), 0 0 6px rgba(56, 189, 248, 0.2) !important;
    }
    [data-testid="stSidebarCollapseButton"] button *,
    [data-testid="stSidebarCollapsedControl"] button * {
        color: #38bdf8 !important;
        fill: #38bdf8 !important;
    }

    /* 파일 다운로드 버튼 통일 규격 */
    div[data-testid="stDownloadButton"] > button,
    .stDownloadButton > button {
        background-color: #334155 !important;
        color: #f8fafc !important;
        border: 1px solid #475569 !important;
        border-radius: 6px !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        height: 38px !important;
        padding: 0 16px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: all 0.2s ease-in-out !important;
    }
    div[data-testid="stDownloadButton"] > button:hover,
    .stDownloadButton > button:hover {
        background-color: #475569 !important;
        border-color: #38bdf8 !important;
        color: #ffffff !important;
        box-shadow: 0 0 10px rgba(56, 189, 248, 0.25) !important;
    }

    /* 사이드바 빠른 선택 컬럼 간격 축소 및 버튼 가로 쓰기 완전 보장 */
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {
        gap: 5px !important;
    }
    [data-testid="stSidebar"] [data-testid="column"] {
        min-width: 0 !important;
        flex: 1 1 0px !important;
    }
    [data-testid="stSidebar"] div.stButton > button {
        border-radius: 6px !important;
        padding: 0 2px !important;
        min-height: 32px !important;
        height: 32px !important;
        width: 100% !important;
    }
    [data-testid="stSidebar"] div.stButton > button * {
        white-space: nowrap !important;
        word-break: keep-all !important;
        overflow-wrap: normal !important;
        writing-mode: horizontal-tb !important;
        font-size: 0.78rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }

    /* KPI 카드 스타일 */
    .kpi-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 14px 16px;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .kpi-label {
        font-size: 0.80rem;
        color: #94a3b8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }
    .kpi-value {
        font-size: 1.45rem;
        font-weight: 700;
        color: #f8fafc;
        line-height: 1.2;
    }
    .kpi-sub {
        font-size: 0.80rem;
        margin-top: 4px;
        font-weight: 500;
    }
    .text-bull {
        color: #f87171 !important; /* 한국 증시 상승: 붉은색 */
    }
    .text-bear {
        color: #60a5fa !important; /* 한국 증시 하락: 푸른색 */
    }
    .text-neutral {
        color: #94a3b8 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# 2. 세션 상태 초기화 & 날짜 연동 로직
# ==============================================================================
expected_latest_day = get_latest_expected_trading_day()
expected_date_obj = datetime.datetime.strptime(expected_latest_day, "%Y-%m-%d").date()

if "selected_period" not in st.session_state:
    st.session_state["selected_period"] = DEFAULT_PERIOD

if "end_date" not in st.session_state:
    st.session_state["end_date"] = expected_date_obj

if "start_date" not in st.session_state:
    # 기본값 1Y
    st.session_state["start_date"] = expected_date_obj - timedelta(days=365)


def apply_period_preset(preset: str):
    """빠른 선택 프리셋 클릭 시 시작일과 종료일을 계산하여 상태 갱신"""
    end_d = expected_date_obj
    st.session_state["selected_period"] = preset
    st.session_state["end_date"] = end_d

    if preset == "3M":
        st.session_state["start_date"] = end_d - timedelta(days=90)
    elif preset == "6M":
        st.session_state["start_date"] = end_d - timedelta(days=180)
    elif preset == "1Y":
        st.session_state["start_date"] = end_d - timedelta(days=365)
    elif preset == "YTD":
        st.session_state["start_date"] = date(end_d.year, 1, 1)
    elif preset == "MAX":
        st.session_state["start_date"] = date(1990, 1, 1)


# ==============================================================================
# 3. [가이드 02] 사이드바 UI/UX 구성 (단일 with st.sidebar 블록)
# ==============================================================================
with st.sidebar:
    # [1단계] 최상단 표준 헤더 카드
    st.markdown(
        """
        <div style='padding: 2px 0 12px 0;'>
            <div style='font-size: 1.25rem; font-weight: 700; color: #f8fafc; letter-spacing: -0.01em; display: flex; align-items: center; gap: 8px;'>
                <span>⚙️</span> 조회 설정
            </div>
            <div style='font-size: 0.82rem; color: #94a3b8; margin-top: 4px; line-height: 1.4;'>
                시장, 지표 및 조회 기간을 설정합니다.
            </div>
        </div>
        <hr style='border: 0; height: 1px; background-color: #334155; margin: 10px 0 16px 0;'>
        """,
        unsafe_allow_html=True
    )

    # [2단계] 시장 선택 (라디오 가로 배치)
    st.markdown("<div style='font-size: 0.95rem; font-weight: 700; color: #e2e8f0; margin-bottom: 6px;'>🏛️ 시장 선택</div>", unsafe_allow_html=True)
    selected_market = st.radio(
        "시장 선택",
        MARKET_OPTIONS,
        index=0,
        horizontal=True,
        label_visibility="collapsed"
    )

    st.markdown("<hr style='border: 0; height: 1px; background-color: #334155; margin: 16px 0;'>", unsafe_allow_html=True)

    # [3단계] 지표 선택 (라디오 가로 배치)
    st.markdown("<div style='font-size: 0.95rem; font-weight: 700; color: #e2e8f0; margin-bottom: 6px;'>📊 지표 선택</div>", unsafe_allow_html=True)
    selected_indicator = st.radio(
        "지표 선택",
        INDICATOR_OPTIONS,
        index=0,
        horizontal=True,
        label_visibility="collapsed"
    )

    st.markdown("<hr style='border: 0; height: 1px; background-color: #334155; margin: 16px 0;'>", unsafe_allow_html=True)

    # [4단계] 조회 기간 캘린더 입력 ("시작일", "종료일" 라벨 삭제 및 캘린더 입력만 유지)
    st.markdown("<div style='font-size: 0.95rem; font-weight: 700; color: #e2e8f0; margin-bottom: 6px;'>📅 조회 기간</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="small")
    with c1:
        input_start = st.date_input(
            "시작일",
            value=st.session_state["start_date"],
            min_value=date(1990, 1, 1),
            max_value=expected_date_obj,
            label_visibility="collapsed"
        )
        if input_start != st.session_state["start_date"]:
            st.session_state["start_date"] = input_start
            st.session_state["selected_period"] = "CUSTOM"

    with c2:
        input_end = st.date_input(
            "종료일",
            value=st.session_state["end_date"],
            min_value=date(1990, 1, 1),
            max_value=expected_date_obj,
            label_visibility="collapsed"
        )
        if input_end != st.session_state["end_date"]:
            st.session_state["end_date"] = input_end
            st.session_state["selected_period"] = "CUSTOM"

    st.markdown("<hr style='border: 0; height: 1px; background-color: #334155; margin: 14px 0 10px 0;'>", unsafe_allow_html=True)

    # [5단계] 빠른 선택 (가로 쓰기 프리셋 버튼 5열)
    st.markdown("<div style='font-size: 0.95rem; font-weight: 700; color: #e2e8f0; margin-bottom: 6px;'>⚡ 빠른 선택</div>", unsafe_allow_html=True)
    preset_cols = st.columns(5, gap="small")
    for idx, p in enumerate(PERIOD_PRESETS):
        with preset_cols[idx]:
            is_active = (st.session_state.get("selected_period") == p)
            btn_type = "primary" if is_active else "secondary"
            if st.button(p, key=f"btn_p_{p}", type=btn_type, use_container_width=True):
                apply_period_preset(p)
                st.rerun()

    st.markdown("<hr style='border: 0; height: 1px; background-color: #334155; margin: 14px 0 10px 0;'>", unsafe_allow_html=True)

    # [6단계] 차트 옵션 설정 (이동평균선 및 로그 스케일 토글)
    st.markdown("<div style='font-size: 0.95rem; font-weight: 700; color: #e2e8f0; margin-bottom: 6px;'>📐 차트 표시 옵션</div>", unsafe_allow_html=True)
    show_ma_lines = st.checkbox(
        "이동평균선 (5, 20, 60, 120일선)",
        value=st.session_state.get("show_ma_lines", True),
        help="주가지수 일봉 캔들차트 위에 5일(단기), 20일(생명선), 60일(수급선), 120일(경기선) 이동평균선을 오버레이합니다.",
        key="chk_ma_lines"
    )
    st.session_state["show_ma_lines"] = show_ma_lines

    use_log_scale = st.checkbox(
        "지수 로그 스케일 (Log Scale)",
        value=st.session_state.get("use_log_scale", False),
        help="장기 시계열에서 주가지수의 복리 성장률과 상승폭을 왜곡 없이 비교합니다. (우측 보조지표는 고유 기준선 유지를 위해 정상 선형 스케일 유지)",
        key="chk_log_scale"
    )
    st.session_state["use_log_scale"] = use_log_scale

    # [7단계] 하단 액션 버튼 (Type A: Update + 조회 2열 배치)
    st.markdown("<hr style='border: 0; height: 1px; background-color: #334155; margin: 18px 0;'>", unsafe_allow_html=True)
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("🔄 Update", use_container_width=True, help="캐시를 초기화하고 최신 데이터를 다시 수집합니다."):
            st.cache_data.clear()
            st.session_state["force_refresh"] = True
            st.rerun()
    with btn_col2:
        if st.button("🔍 조회", type="primary", use_container_width=True, help="선택한 조건으로 화면을 갱신합니다."):
            st.rerun()


# ==============================================================================
# 4. 데이터 로딩 (캐시 바인딩 및 가이드 04, 05 준수)
# ==============================================================================
force_refresh = st.session_state.pop("force_refresh", False)
DATASET_SCHEMA_VERSION = "20261026_v7_candlestick_ma"

@st.cache_data(ttl=1800, show_spinner=False)
def load_cached_dataset(market_choice: str, target_date_key: str, schema_ver: str = DATASET_SCHEMA_VERSION, force_refresh: bool = False) -> pd.DataFrame:
    """[가이드 04, 05] 최신 거래일 키 및 스키마 버전을 바인딩하여 15:45 마감 후 또는 구조 변경 시 자동 갱신되는 캐시 함수"""
    return get_market_balance_dataset(market_choice=market_choice, force_refresh=force_refresh)

with st.spinner("한국 증시 밸런스 데이터를 수집 및 분석하는 중..."):
    df_raw = load_cached_dataset(selected_market, expected_latest_day, DATASET_SCHEMA_VERSION, force_refresh=force_refresh)

# 확장 컬럼 존재 여부 자가 치유(Self-Healing) 방어 코드
REQUIRED_EXT_COLS = [
    "credit_jo", "deposit_jo", "vkospi", "foreign_cum_jo", "inst_cum_jo",
    "above_200ma", "foreign_daily_eok", "inst_daily_eok", "ma5", "ma20", "ma60", "ma120"
]
if df_raw.empty or any(col not in df_raw.columns for col in REQUIRED_EXT_COLS):
    st.cache_data.clear()
    df_raw = get_market_balance_dataset(market_choice=selected_market, force_refresh=True)


# ==============================================================================
# 5. 오른쪽 메인 화면 렌더링
# ==============================================================================

# (1) [가이드 01] 메인 타이틀(H1) 및 서브타이틀 규격
st.markdown(
    f"""
    <div style='text-align: center; padding-top: 1.0rem;'>
        <h1 style='color: #8AB4F8; font-size: 2.0rem; font-weight: 800; margin-bottom: 6px;'>{MAIN_TITLE}</h1>
        <p style='color: #94a3b8; font-size: 0.95rem; margin-bottom: 16px;'>{SUB_TITLE}</p>
        <hr style='border: 0; height: 1px; background-color: #334155; margin: 16px 0 24px 0;'>
    </div>
    """,
    unsafe_allow_html=True
)

if df_raw.empty or ("date" not in df_raw.columns):
    st.error("데이터를 불러오지 못했습니다. 사이드바의 [🔄 Update] 버튼을 눌러 다시 시도해 주세요.")
    st.stop()

# (2) 날짜 필터링
s_str = st.session_state["start_date"].strftime("%Y-%m-%d")
e_str = st.session_state["end_date"].strftime("%Y-%m-%d")

df_filtered = df_raw[(df_raw["date"] >= s_str) & (df_raw["date"] <= e_str)].copy()
df_filtered = df_filtered.sort_values("date").reset_index(drop=True)

if df_filtered.empty:
    st.warning(f"선택하신 기간({s_str} ~ {e_str})에 해당하는 거래일 데이터가 없습니다.")
    st.stop()

# [외인&기관수급: 조회 기간 상대 누적 순매수 산출]
# HTS 및 KRX 증시 금융정보 표준: 선택된 조회 기간 내의 일별 순매수액(daily net buy)을 누적
# 조회 기간 시작일 이전의 과거 누적분은 배제하고, 시작일(0.0)을 기준으로 기간 내 자금 유입(+) 및 유출(-)을 정확히 반영
if "foreign_daily_eok" in df_filtered.columns and df_filtered["foreign_daily_eok"].notna().any():
    df_filtered["foreign_cum_jo"] = (df_filtered["foreign_daily_eok"].cumsum() / 10000.0).round(2)
    df_filtered["inst_cum_jo"] = (df_filtered["inst_daily_eok"].cumsum() / 10000.0).round(2)
elif "foreign_cum_jo" in df_filtered.columns and len(df_filtered) > 0:
    # 폴백: 시작일 값을 기준으로 차감하여 시작일을 0으로 재기준화(Re-basing)
    df_filtered["foreign_cum_jo"] = (df_filtered["foreign_cum_jo"] - df_filtered["foreign_cum_jo"].iloc[0]).round(2)
    df_filtered["inst_cum_jo"] = (df_filtered["inst_cum_jo"] - df_filtered["inst_cum_jo"].iloc[0]).round(2)

# (3) 최신 데이터 요약 수치 계산
latest_row = df_filtered.iloc[-1]
prev_row = df_filtered.iloc[-2] if len(df_filtered) >= 2 else latest_row

latest_close = latest_row["close"]
prev_close = prev_row["close"]
close_chg = latest_close - prev_close
close_chg_pct = (close_chg / prev_close) * 100.0 if prev_close != 0 else 0.0

# 등락 텍스트 및 컬러 클래스
bull_class = "text-bull" if close_chg >= 0 else "text-bear"
chg_sign = "+" if close_chg > 0 else ""
close_sub_html = f"<span class='{bull_class}'>{chg_sign}{close_chg:,.2f}pt ({chg_sign}{close_chg_pct:.2f}%)</span>"

meta = INDICATOR_META.get(selected_indicator, {})

# 보조지표 요약값 계산
if selected_indicator == "PER":
    val_latest = latest_row.get("per", np.nan)
    val_prev = prev_row.get("per", np.nan)
    val_str = f"{val_latest:.2f}배" if pd.notna(val_latest) else "N/A"
    diff = val_latest - val_prev if (pd.notna(val_latest) and pd.notna(val_prev)) else 0.0
    diff_sign = "+" if diff > 0 else ""
    val_sub_html = f"<span class='text-neutral'>전일대비 {diff_sign}{diff:.2f}배</span>"
    
    # 상태 진단
    if pd.notna(val_latest):
        if val_latest < 10.0:
            status_text = "🟢 역사적 저평가 (이익 안전마진 구간)"
        elif val_latest > 16.0:
            status_text = "🔴 고평가 주의 (이익 대비 과열 구간)"
        else:
            status_text = "⚪ 적정 밸류에이션 구간"
    else:
        status_text = "데이터 확인 중"

elif selected_indicator == "PBR":
    val_latest = latest_row.get("pbr", np.nan)
    val_prev = prev_row.get("pbr", np.nan)
    val_str = f"{val_latest:.2f}배" if pd.notna(val_latest) else "N/A"
    diff = val_latest - val_prev if (pd.notna(val_latest) and pd.notna(val_prev)) else 0.0
    diff_sign = "+" if diff > 0 else ""
    val_sub_html = f"<span class='text-neutral'>전일대비 {diff_sign}{diff:.2f}배</span>"

    if pd.notna(val_latest):
        if val_latest < 1.0:
            status_text = "🟢 자산가치 청산선 하회 (극단적 바닥권)"
        elif val_latest > 1.4:
            status_text = "🔴 장부가치 대비 프리미엄 구간"
        else:
            status_text = "⚪ 적정 자산평가 구간"
    else:
        status_text = "데이터 확인 중"

elif selected_indicator == "RSI":
    val_latest = latest_row.get("rsi_20", np.nan)
    val_prev = prev_row.get("rsi_20", np.nan)
    val_str = f"{val_latest:.1f}" if pd.notna(val_latest) else "N/A"
    diff = val_latest - val_prev if (pd.notna(val_latest) and pd.notna(val_prev)) else 0.0
    diff_sign = "+" if diff > 0 else ""
    val_sub_html = f"<span class='text-neutral'>전일대비 {diff_sign}{diff:.1f}pt</span>"

    if pd.notna(val_latest):
        if val_latest >= 70.0:
            status_text = "🔴 과매수 국면 (조정 및 차익실현 경계)"
        elif val_latest <= 30.0:
            status_text = "🟢 과매도 국면 (기술적 반등 유효 구간)"
        elif val_latest >= 50.0:
            status_text = "⚪ 상승 모멘텀 우세 (50 상회)"
        else:
            status_text = "⚪ 하락 모멘텀 우세 (50 하회)"
    else:
        status_text = "데이터 확인 중"

elif selected_indicator == "ADR":
    adr14 = latest_row.get("adr_14", np.nan)
    adr1 = latest_row.get("adr_1", np.nan)
    val_str = f"{adr14:.1f}%" if pd.notna(adr14) else "N/A"
    adr1_str = f"{adr1:.1f}%" if pd.notna(adr1) else "N/A"
    val_sub_html = f"<span class='text-neutral'>당일 ADR(1): <b>{adr1_str}</b></span>"

    if pd.notna(adr14):
        if adr14 >= 120.0:
            status_text = "🔴 과열권 (120% 상회: 차익실현 분할매도 구간)"
        elif adr14 <= 75.0:
            status_text = "🟢 침체/바닥권 (75% 하회: 저점 매수 기회 구간)"
        else:
            status_text = "⚪ 정상 균형 범위 (75% ~ 120%)"
    else:
        status_text = "데이터 확인 중"

elif selected_indicator == "예탁금&신용":
    # 금융투자협회(KOFIA) 공식 결제 공시(T+1 집계) 지연을 고려하여 최신 공시 거래일 기준 추출
    valid_dep_rows = df_filtered.dropna(subset=["deposit_jo", "credit_jo"])
    if not valid_dep_rows.empty:
        kofia_row = valid_dep_rows.iloc[-1]
        kofia_date = kofia_row["date"]
        val_dep = kofia_row["deposit_jo"]
        val_cred = kofia_row["credit_jo"]
        val_str = f"예탁 {val_dep:.1f}조 / 신용 {val_cred:.1f}조"
        ratio = (val_cred / val_dep * 100.0) if (val_dep and val_dep > 0 and pd.notna(val_cred)) else np.nan
        ratio_str = f"{ratio:.1f}%" if pd.notna(ratio) else "N/A"

        if len(valid_dep_rows) >= 2:
            prev_kofia_row = valid_dep_rows.iloc[-2]
            dep_diff = val_dep - prev_kofia_row["deposit_jo"]
            dep_sign = "+" if dep_diff > 0 else ""
            cred_diff = val_cred - prev_kofia_row["credit_jo"]
            cred_sign = "+" if cred_diff > 0 else ""
            val_sub_html = f"<span class='text-neutral'>금투협({kofia_date}): 예탁 <b>{dep_sign}{dep_diff:.1f}조</b> / 신용 <b>{cred_sign}{cred_diff:.1f}조</b></span>"
        else:
            val_sub_html = f"<span class='text-neutral'>금투협(KOFIA) 최종 공시일: <b>{kofia_date}</b> (신용비율: {ratio_str})</span>"
    else:
        val_str = "N/A"
        val_sub_html = "<span class='text-neutral'>공시 데이터 확인 중</span>"
        ratio = np.nan

    if pd.notna(ratio):
        if ratio >= 40.0:
            status_text = "🔴 신용 레버리지 과열 (변동성 확대 및 반대매매 주의)"
        elif ratio <= 28.0:
            status_text = "🟢 신용 리스크 해소 (대기자금 풍부, 반등 안전마진)"
        else:
            status_text = f"⚪ 적정 수급 균형 (신용비율 {ratio:.1f}%)"
    else:
        status_text = "데이터 확인 중"

elif selected_indicator == "VKOSPI":
    val_latest = latest_row.get("vkospi", np.nan)
    val_prev = prev_row.get("vkospi", np.nan)
    val_str = f"{val_latest:.2f}pt" if pd.notna(val_latest) else "N/A"
    diff = val_latest - val_prev if (pd.notna(val_latest) and pd.notna(val_prev)) else 0.0
    diff_sign = "+" if diff > 0 else ""
    val_sub_html = f"<span class='text-neutral'>전일대비 {diff_sign}{diff:.2f}pt</span>"

    if pd.notna(val_latest):
        if val_latest >= 30.0:
            status_text = "🟢 극단적 공포 국면 (30pt 상회: 역발상 매수 기회)"
        elif val_latest <= 15.0:
            status_text = "🔴 극단적 낙관 국면 (15pt 하회: 고점 상투 경계)"
        else:
            status_text = "⚪ 정상 변동성 안정 구간 (15pt ~ 30pt)"
    else:
        status_text = "데이터 확인 중"

elif selected_indicator == "외인&기관수급":
    for_cum = latest_row.get("foreign_cum_jo", np.nan)
    inst_cum = latest_row.get("inst_cum_jo", np.nan)
    val_str = f"외 {for_cum:+.1f}조 / 기 {inst_cum:+.1f}조" if (pd.notna(for_cum) and pd.notna(inst_cum)) else "N/A"
    
    # 최신 당일 순매수 (억원 단위로 직관적 표시)
    for_d_eok = latest_row.get("foreign_daily_eok", np.nan)
    inst_d_eok = latest_row.get("inst_daily_eok", np.nan)
    if pd.isna(for_d_eok) and len(df_filtered) >= 2:
        for_p = prev_row.get("foreign_cum_jo", 0.0)
        inst_p = prev_row.get("inst_cum_jo", 0.0)
        for_d_eok = (for_cum - for_p) * 10000.0
        inst_d_eok = (inst_cum - inst_p) * 10000.0

    for_d_sign = "+" if (pd.notna(for_d_eok) and for_d_eok > 0) else ""
    inst_d_sign = "+" if (pd.notna(inst_d_eok) and inst_d_eok > 0) else ""
    val_sub_html = f"<span class='text-neutral'>당일: 외인 <b>{for_d_sign}{for_d_eok:,.0f}억</b> / 기관 <b>{inst_d_sign}{inst_d_eok:,.0f}억</b></span>"

    if pd.notna(for_cum) and pd.notna(inst_cum):
        if for_cum > 0 and inst_cum > 0:
            status_text = "🔴 메이저 쌍끌이 순매수 우세 (지수 상승 견인)"
        elif for_cum < 0 and inst_cum < 0:
            status_text = "🔵 메이저 동반 순매도 우세 (지수 하방 압력)"
        elif for_cum > 0 and inst_cum <= 0:
            status_text = "⚪ 외국인 순매수 유입 (기관 매도 방어)"
        elif for_cum < 0 and inst_cum >= 0:
            status_text = "⚪ 기관 방어 매수 및 외국인 지속 순매도"
        else:
            status_text = "⚪ 외인·기관 수급 공방"
    else:
        status_text = "데이터 확인 중"

elif selected_indicator == "200일선상회":
    val_latest = latest_row.get("above_200ma", np.nan)
    val_prev = prev_row.get("above_200ma", np.nan)
    val_str = f"{val_latest:.1f}%" if pd.notna(val_latest) else "N/A"
    diff = val_latest - val_prev if (pd.notna(val_latest) and pd.notna(val_prev)) else 0.0
    diff_sign = "+" if diff > 0 else ""
    val_sub_html = f"<span class='text-neutral'>전일대비 {diff_sign}{diff:.1f}%p</span>"

    if pd.notna(val_latest):
        if val_latest >= 75.0:
            status_text = "🔴 시장 전반 과열권 (75% 상회: 차익실현 경계)"
        elif val_latest <= 25.0:
            status_text = "🟢 시장 극단적 침체/투매 (25% 하회: 역사적 바닥 형성)"
        elif val_latest >= 50.0:
            status_text = "⚪ 시장 절반 이상 장기 상승 추세 (50% 상회)"
        else:
            status_text = "⚪ 시장 절반 이상 장기 하락 추세 (50% 하회)"
    else:
        status_text = "데이터 확인 중"

# (4) KPI 요약 카드 4열 배치
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.markdown(
        f"""
        <div class='kpi-card'>
            <div class='kpi-label'>{selected_market} 최신 지수</div>
            <div class='kpi-value'>{latest_close:,.2f}</div>
            <div class='kpi-sub'>{close_sub_html} ({latest_row['date']})</div>
        </div>
        """,
        unsafe_allow_html=True
    )

kpi2_label = f"{meta.get('short_name', selected_indicator)} 기간 누적" if selected_indicator == "외인&기관수급" else f"{meta.get('short_name', selected_indicator)} 현재 수치"

with kpi2:
    st.markdown(
        f"""
        <div class='kpi-card'>
            <div class='kpi-label'>{kpi2_label}</div>
            <div class='kpi-value'>{val_str}</div>
            <div class='kpi-sub'>{val_sub_html}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with kpi3:
    st.markdown(
        f"""
        <div class='kpi-card'>
            <div class='kpi-label'>시장 상태 진단 (Balance)</div>
            <div class='kpi-value' style='font-size: 1.02rem; padding-top: 4px;'>{status_text}</div>
            <div class='kpi-sub'><span class='text-neutral'>설정 지표 기준 시그널</span></div>
        </div>
        """,
        unsafe_allow_html=True
    )

with kpi4:
    # 조회 기간 내 통계 (최고/최저/평균) - 컬럼 유무를 안전하게 체크하여 KeyError 원천 차단
    col_map = {
        "PER": ("per", "배", ""),
        "PBR": ("pbr", "배", ""),
        "RSI": ("rsi_20", "pt", ""),
        "ADR": ("adr_14", "%", "ADR(14) "),
        "예탁금&신용": ("credit_jo", "조", "신용 "),
        "VKOSPI": ("vkospi", "pt", ""),
        "외인&기관수급": ("foreign_cum_jo", "조", "외인 "),
        "200일선상회": ("above_200ma", "%", "")
    }
    target_col, unit_label, stat_prefix = col_map.get(selected_indicator, ("close", "pt", ""))

    if selected_indicator == "외인&기관수급":
        for_min = df_filtered["foreign_cum_jo"].min()
        for_max = df_filtered["foreign_cum_jo"].max()
        inst_min = df_filtered["inst_cum_jo"].min()
        inst_max = df_filtered["inst_cum_jo"].max()
        stat_text = f"외 {for_min:+.1f}~{for_max:+.1f}조 / 기 {inst_min:+.1f}~{inst_max:+.1f}조"
    elif target_col in df_filtered.columns:
        series_stat = df_filtered[target_col].dropna()
        if not series_stat.empty:
            stat_min = series_stat.min()
            stat_max = series_stat.max()
            stat_mean = series_stat.mean()
            stat_text = f"{stat_prefix}최저 {stat_min:.1f} / 평균 {stat_mean:.1f} / 최고 {stat_max:.1f}{unit_label}"
        else:
            stat_text = "N/A"
    else:
        stat_text = "N/A"

    period_sub = f"{s_str} ~ {valid_dep_rows.iloc[-1]['date']} (금투협 공시)" if (selected_indicator == "예탁금&신용" and 'valid_dep_rows' in locals() and not valid_dep_rows.empty) else f"{s_str} ~ {e_str}"

    st.markdown(
        f"""
        <div class='kpi-card'>
            <div class='kpi-label'>조회 기간 통계 ({len(df_filtered)}거래일)</div>
            <div class='kpi-value' style='font-size: 1.02rem; padding-top: 4px;'>{stat_text}</div>
            <div class='kpi-sub'><span class='text-neutral'>{period_sub}</span></div>
        </div>
        """,
        unsafe_allow_html=True
    )

# (5) [가이드 01 Level 2] 본문 메인 섹터 제목 (차트)
scale_badge = " <span style='font-size: 0.80rem; background-color: #334155; color: #38bdf8; padding: 2px 8px; border-radius: 4px; font-weight: 600; vertical-align: middle; margin-left: 6px;'>로그 스케일</span>" if use_log_scale else ""
ma_badge = " <span style='font-size: 0.80rem; background-color: #1e293b; border: 1px solid #334155; color: #f59e0b; padding: 2px 8px; border-radius: 4px; font-weight: 600; vertical-align: middle; margin-left: 6px;'>이평선 (5, 20, 60, 120)</span>" if show_ma_lines else ""
st.markdown(
    f"<div style='font-size: 1.20rem; color: #8AB4F8; font-weight: 700; margin: 20px 0 10px 0;'>"
    f"📈 {selected_market} 일봉 & {meta.get('short_name', selected_indicator)} 비교 차트{scale_badge}{ma_badge}"
    f"</div>",
    unsafe_allow_html=True
)

# (6) [가이드 03] 고대비 합성 차트 렌더링
fig = create_market_balance_chart(
    df=df_filtered,
    market_name=selected_market,
    indicator_name=selected_indicator,
    use_log_scale=use_log_scale,
    show_ma_lines=show_ma_lines
)
st.plotly_chart(fig, use_container_width=True)

# (7) 지표 해설 및 전략적 가이드 박스
with st.expander(f"💡 {meta.get('name', selected_indicator)} 지표 해석 및 활용 가이드", expanded=False):
    st.markdown(
        f"""
        <div style='color: #cbd5e1; font-size: 0.90rem; line-height: 1.6;'>
            <p><b>■ 지표 개요:</b> {meta.get('desc')}</p>
        """,
        unsafe_allow_html=True
    )
    if selected_indicator == "PER":
        st.markdown("""
        - **투자 전략 관점**: KOSPI의 역사적 평균 PER은 통상 10~12배 수준입니다. 10배 이하는 기업 이익 대비 주가가 저평가되어 강력한 하방 경직성을 제공하는 분할 매수 적기이며, 14~16배 상회 시에는 실적 성장이 동반되지 않으면 밸류에이션 부담이 가중됩니다.
        </div>""", unsafe_allow_html=True)
    elif selected_indicator == "PBR":
        st.markdown("""
        - **투자 전략 관점**: KOSPI PBR 1.0배는 대한민국 상장기업들의 순자산(장부가치)과 시가총액이 일치하는 지점입니다. 역사적으로 한국 증시에서 PBR 0.85~0.95배는 금융위기나 팬데믹급 충격 시에만 나타나는 역사적 최저점 바닥권역이었습니다.
        </div>""", unsafe_allow_html=True)
    elif selected_indicator == "RSI":
        st.markdown("""
        - **투자 전략 관점**: RSI(20)은 단기 노이즈를 완화하고 중기 추세를 읽기에 가장 적합한 주기입니다. 70 이상에서는 추격 매수를 자제하고 이익 실현을 고려하며, 30 이하로 급락했을 때는 투매(Panic Selling) 이후 기술적 반등을 노리는 전략이 유효합니다.
        </div>""", unsafe_allow_html=True)
    elif selected_indicator == "ADR":
        st.markdown("""
        - **투자 전략 관점**: ADR(Advance Decline Ratio)은 시가총액 상위 대형주 몇 개가 지수를 왜곡할 때 시장 전체 종목의 실제 체감 온도를 정확히 보여줍니다.
        - **ADR(14) 120% 이상**: 시장 전체가 과열되어 다수의 종목이 단기 고점에 도달한 경계 구간입니다.
        - **ADR(14) 75% 이하**: 시장 전체 종목의 3/4 이상이 하락한 극단적 침체/바닥권으로, 확률적으로 가장 높은 중장기 반등 기회를 제공합니다.
        - **당일 ADR(1)**: 하루 동안의 극단적 등락 쏠림을 즉각 감지합니다.
        </div>""", unsafe_allow_html=True)
    elif selected_indicator == "예탁금&신용":
        st.markdown("""
        - **공식 출처 및 결제 공시 주기(T+1)**: 금융투자협회(KOFIA FreeSIS)의 공식 '투자자예탁금' 및 '신용공여잔고' 통계를 직접 연동합니다. 국내 증권 결제 주기(T+2) 특성상 <b>익영업일 저녁(T+1)에 전 거래일 수치가 공식 확정 공시</b>되므로, 당일 데이터는 미발표(공시 대기) 상태로 유지되고 전 거래일 확정치가 최종치로 표기됩니다.
        - **투자 전략 관점**: 고객예탁금은 증시 진입 대기성 자금이며, 신용융자 잔고는 빚을 내어 주식을 매수한 레버리지 자금입니다.
        - **레버리지 과열**: 예탁금 대비 신용잔고 비율이 40%를 상회하면 지수 소폭 하락에도 반대매매 매물이 쏟아지는 악순환이 발생할 수 있습니다.
        - **신용 반대매매 후 바닥**: 지수 급락과 함께 신용잔고가 연일 수천억 원씩 급감(투매 및 반대매매 청산 완료)한 직후는 역사적으로 가장 강력한 V자 반등 바닥권이었습니다.
        </div>""", unsafe_allow_html=True)
    elif selected_indicator == "VKOSPI":
        st.markdown("""
        - **투자 전략 관점**: KOSPI 200 옵션 가격에 반영된 향후 30일간의 시장 내재변동성을 나타내는 한국형 공포지수(Volatility Index)입니다.
        - **패닉 바닥권 (30pt 이상)**: 시장 참여자들의 극단적 공포와 투매가 절정에 달했을 때 급등하며, 역사적으로 워런 버핏의 '남들이 두려워할 때 탐욕을 가져라'는 역발상 분할 매수 적기였습니다.
        - **안도 상투권 (15pt 이하)**: 시장에 낙관론과 방심이 팽배해진 상태로, 작은 충격에도 변동성이 확대될 수 있으므로 현금 비중 확대를 고려해야 하는 경계 구간입니다.
        </div>""", unsafe_allow_html=True)
    elif selected_indicator == "외인&기관수급":
        st.markdown("""
        - **투자 전략 관점**: 한국 증시는 시가총액의 30% 이상을 보유한 외국인 투자자의 자금 흐름에 의해 방향성이 결정되는 대표적인 외국인 주도 시장입니다.
        - **쌍끌이 매수/매도**: 외국인과 기관이 동시에 순매수(쌍끌이)하는 국면은 강력한 추세 상승장이 지속되며, 동반 순매도 국면에서는 지수 반등이 제한됩니다.
        - **다이버전스(Divergence)**: 주가지수는 상승하는데 외국인 누적 순매수가 감소하거나, 주가는 횡보하는데 외국인이 지속 매집하는 다이버전스는 조만간 큰 추세 반전을 예고하는 강력한 선행 시그널입니다.
        </div>""", unsafe_allow_html=True)
    elif selected_indicator == "200일선상회":
        st.markdown("""
        - **투자 전략 관점**: 시장 전체 종목 중 200일 장기 이동평균선(기관/외국인의 1년 평균 매입 단가)을 상회하는 종목의 비율로, 시장 건전성(Market Breadth)을 가장 정밀하게 측정합니다.
        - **과열/천장권 (75% 이상)**: 대다수 종목이 장기 이평선을 넘어 상승 피로도가 누적된 상태로, 단기 고점 형성 및 차익 실현 매물 출회에 주의해야 합니다.
        - **투매/바닥권 (25% 이하)**: 시장의 75% 이상 종목이 장기 이평선 아래로 추락한 극단적 침체 국면으로, 하락 추세의 막바지이자 밸류에이션 매력이 극대화되는 역사적 분할 매수 기회입니다.
        </div>""", unsafe_allow_html=True)

    st.markdown("""
    <hr style='border: 0; height: 1px; background-color: #334155; margin: 12px 0 8px 0;'>
    <div style='color: #94a3b8; font-size: 0.84rem; line-height: 1.5;'>
        📐 <b>로그 스케일(Log Scale) 분석 팁</b>: 수년 이상의 장기 시계열이나 'MAX' 기간 조회 시에는 복리 효과로 인해 최근의 변동폭이 과장되어 보이고 과거의 거대한 파동(외환위기, 금융위기 등)이 축소되어 보입니다. 사이드바의 <b>[지수 로그 스케일]</b>을 체크하시면 역사적 상승률과 하락폭을 왜곡 없는 동일 비율 척도로 정밀 비교하실 수 있습니다.
    </div>
    """, unsafe_allow_html=True)

# (8) [가이드 01 Level 2] 본문 데이터 테이블 섹터
st.markdown(
    f"<div style='font-size: 1.20rem; color: #8AB4F8; font-weight: 700; margin: 26px 0 10px 0;'>"
    f"📋 {selected_market} 일별 세부 데이터 (최근 거래일 순)"
    f"</div>",
    unsafe_allow_html=True
)

# 테이블용 데이터 정제
df_table = df_filtered.copy().sort_values("date", ascending=False).reset_index(drop=True)
rename_dict = {
    "date": "거래일자",
    "close": f"{selected_market} 종가",
    "open": "시가",
    "high": "고가",
    "low": "저가",
    "volume": "거래량",
    "per": "PER (배)",
    "pbr": "PBR (배)",
    "div_yield": "배당수익률 (%)",
    "rsi_20": "RSI(20)",
    "adv": "상승 종목수",
    "dec": "하락 종목수",
    "adr_1": "당일 ADR(1) (%)",
    "adr_14": "ADR(14) (%)",
    "deposit_jo": "고객예탁금 (조 원)",
    "credit_jo": "신용잔고 (조 원)",
    "credit_ratio": "신용비율 (%)",
    "vkospi": "VKOSPI (pt)",
    "foreign_cum_jo": "외인 누적순매수 (조 원)",
    "inst_cum_jo": "기관 누적순매수 (조 원)",
    "above_200ma": "200일선 상회비율 (%)"
}

# 기본 공통 컬럼: 거래일자, 종가
base_cols = ["date", "close"]
if selected_indicator == "PER":
    indicator_cols = ["per", "pbr", "div_yield"]
elif selected_indicator == "PBR":
    indicator_cols = ["pbr", "per", "div_yield"]
elif selected_indicator == "RSI":
    indicator_cols = ["rsi_20"]
elif selected_indicator == "ADR":
    indicator_cols = ["adv", "dec", "adr_1", "adr_14"]
elif selected_indicator == "예탁금&신용":
    indicator_cols = ["deposit_jo", "credit_jo", "credit_ratio"]
elif selected_indicator == "VKOSPI":
    indicator_cols = ["vkospi"]
elif selected_indicator == "외인&기관수급":
    indicator_cols = ["foreign_cum_jo", "inst_cum_jo"]
elif selected_indicator == "200일선상회":
    indicator_cols = ["above_200ma"]
else:
    indicator_cols = []

all_possible_cols = ["rsi_20", "per", "pbr", "adr_14", "deposit_jo", "credit_jo", "vkospi", "foreign_cum_jo", "inst_cum_jo", "above_200ma"]
remaining_cols = [c for c in all_possible_cols if c not in indicator_cols and c not in base_cols]
cols_to_show = base_cols + indicator_cols + remaining_cols
existing_cols = [c for c in cols_to_show if c in df_table.columns]
df_display = df_table[existing_cols].rename(columns=rename_dict)

# 포맷팅
st.dataframe(
    df_display,
    use_container_width=True,
    height=280,
    hide_index=True
)

# (9) [가이드 01 (3)] 파일 다운로드 버튼 통일 규격 (CSV / Excel 2열 배치)
col_dl1, col_dl2 = st.columns(2)

csv_data = df_display.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

excel_buffer = io.BytesIO()
with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
    df_display.to_excel(writer, index=False, sheet_name="MarketBalance")
excel_data = excel_buffer.getvalue()

file_base_name = f"MarketBalance_{selected_market.split()[0]}_{selected_indicator}_{s_str}_{e_str}"

with col_dl1:
    st.download_button(
        label="📥 CSV 파일 다운로드",
        data=csv_data,
        file_name=f"{file_base_name}.csv",
        mime="text/csv",
        use_container_width=True
    )
with col_dl2:
    st.download_button(
        label="📥 엑셀 파일 다운로드",
        data=excel_data,
        file_name=f"{file_base_name}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# (10) [가이드 01 (2)] 하단 법적 책임 및 투자 유의사항 고지 푸터
st.markdown("<hr style='border: 0; height: 1px; background-color: #334155; margin: 30px 0 10px 0;'>", unsafe_allow_html=True)
st.markdown(
    f"<div style='text-align: center; color: #64748b; font-size: 0.8rem; margin-top: 8px; margin-bottom: 24px; line-height: 1.6;'>"
    f"{DISCLAIMER_TEXT}"
    f"</div>",
    unsafe_allow_html=True
)
