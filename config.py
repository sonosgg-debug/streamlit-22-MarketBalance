"""
config.py
Market Balance 앱의 전역 설정, 상수, 메타데이터 및 차트 테마 정의.
00 App_AI_Template 공통 가이드(01, 02, 03, 04, 05, 06) 준수.
"""

import os
from datetime import timezone, timedelta

# KST 타임존
KST = timezone(timedelta(hours=9))

# 앱 메인 텍스트 상수
APP_TITLE = "Market Balance"
APP_ICON = "📈"
MAIN_TITLE = "한국 증시 Now : Valuation & Balance"
SUB_TITLE = "코스피 (KOSPI)와 코스닥(KOSDAQ)의 주가지수와 PER, PBR, RSI, ADR 등의 보조지표를 통해 시장의 방향성을 추적합니다."
DISCLAIMER_TEXT = "⚠️ 본 서비스에서 제공하는 모든 정보는 투자 참고용이며, 투자의 최종 결정과 책임은 투자자 본인에게 있습니다."

# 시장 옵션 (가이드 02 및 사용자 요구사항 반영)
MARKET_OPTIONS = ["코스피 (KOSPI)", "코스닥 (KOSDAQ)"]
DEFAULT_MARKET = "코스피 (KOSPI)"

# 시장 키 매핑 (공백 유무 모두 수용)
MARKET_KEY_MAP = {
    "코스피 (KOSPI)": "KOSPI",
    "코스피(KOSPI)": "KOSPI",
    "KOSPI": "KOSPI",
    "코스닥 (KOSDAQ)": "KOSDAQ",
    "코스닥(KOSDAQ)": "KOSDAQ",
    "KOSDAQ": "KOSDAQ",
}

# 네이버 fchart 심볼
NAVER_INDEX_MAP = {
    "KOSPI": "KOSPI",
    "KOSDAQ": "KOSDAQ",
}

# yfinance 티커 (폴백용)
YFINANCE_INDEX_MAP = {
    "KOSPI": "^KS11",
    "KOSDAQ": "^KQ11",
}

# KRX 인덱스 코드 (pykrx용)
KRX_INDEX_CODE_MAP = {
    "KOSPI": "1001",
    "KOSDAQ": "2001",
}

# 지표 옵션
INDICATOR_OPTIONS = ["PER", "PBR", "RSI", "ADR", "예탁금&신용", "VKOSPI", "외인&기관수급", "200일선상회"]
DEFAULT_INDICATOR = "PER"

# 기간 선택 프리셋
PERIOD_PRESETS = ["3M", "6M", "1Y", "YTD", "MAX"]
DEFAULT_PERIOD = "1Y"

# 지표별 메타데이터
INDICATOR_META = {
    "PER": {
        "name": "PER (주가수익비율)",
        "short_name": "PER",
        "chart_label": "PER (배)",
        "unit": "배",
        "format": "{:.2f}배",
        "desc": "주가를 주당순이익(EPS)으로 나눈 값으로, 시장 전체의 이익 대비 밸류에이션 수준을 나타냅니다. 낮을수록 기업 이익 대비 주가가 저평가되어 있음을 의미합니다.",
        "line_color": "#F59E0B",  # Amber / Gold
        "has_bands": True,
        "is_breadth": False,
    },
    "PBR": {
        "name": "PBR (주가순자산비율)",
        "short_name": "PBR",
        "chart_label": "PBR (배)",
        "unit": "배",
        "format": "{:.2f}배",
        "desc": "주가를 주당순자산(BPS)으로 나눈 값으로, 청산가치 대비 시장 평가 수준과 역사적 안전마진을 확인합니다. 1.0배 이하는 자산가치 대비 극도의 저평가 구간입니다.",
        "line_color": "#10B981",  # Emerald Green
        "has_bands": True,
        "is_breadth": False,
    },
    "RSI": {
        "name": "RSI(20) (상대강도지수)",
        "short_name": "RSI(20)",
        "chart_label": "RSI(20)",
        "unit": "pt",
        "format": "{:.1f}",
        "desc": "최근 20거래일 동안의 주가 상승폭과 하락폭의 상대 강도를 측정하여 과매수(70+)와 과매도(30-) 국면을 진단합니다. 50 이상은 상승 우세, 50 이하는 하락 우세를 뜻합니다.",
        "line_color": "#A855F7",  # Purple
        "overbought": 70.0,
        "oversold": 30.0,
        "midline": 50.0,
        "has_bands": True,
        "is_breadth": False,
    },
    "ADR": {
        "name": "ADR (등락비율, Advance Decline Ratio)",
        "short_name": "ADR(14) & ADR(1)",
        "chart_label": "ADR (%)",
        "unit": "%",
        "format": "{:.1f}%",
        "desc": "하락 종목 수 대비 상승 종목 수의 비율로 시장의 실제 참여도와 체감 온도를 측정합니다. ADR(14)는 14일 누적 추세선(120% 이상 과열, 75% 이하 바닥권), ADR(1)은 당일 등락비율입니다.",
        "line_color_14": "#EC4899",  # Rose Pink (ADR 14)
        "line_color_1": "rgba(148, 163, 184, 0.45)",   # Slate 400 (ADR 1)
        "overbought": 120.0,
        "oversold": 75.0,
        "midline": 100.0,
        "has_bands": True,
        "is_breadth": True,
    },
    "예탁금&신용": {
        "name": "고객예탁금 & 신용잔고",
        "short_name": "예탁금/신용",
        "chart_label": "자금 규모 (조 원)",
        "unit": "조 원",
        "format": "{:.1f}조 원",
        "desc": "금융투자협회(KOFIA FreeSIS) 공식 결제 공시(T+1 결제 집계) 기준의 투자자예탁금(대기자금)과 신용공여잔고(레버리지) 추이입니다. 결제 주기(T+1)로 인해 전 거래일 확정치까지 공시되며, 신용잔고 급증은 과열을, 반대매매 이후 급감은 역사적 바닥을 시사합니다.",
        "line_color": "#F59E0B",      # Warm Amber Gold (축 및 기본 색상)
        "line_color_dep": "#F59E0B",  # Warm Amber Gold (고객예탁금: 지수 하늘색과 완벽 대비)
        "line_color_cred": "#F43F5E", # Rose Red (신용잔고)
        "has_bands": False,
        "is_breadth": False,
    },
    "VKOSPI": {
        "name": "VKOSPI (코스피 200 변동성지수)",
        "short_name": "VKOSPI",
        "chart_label": "변동성 (pt)",
        "unit": "pt",
        "format": "{:.2f}",
        "desc": "KOSPI 200 옵션 가격을 기반으로 산출되는 한국형 VIX 공포지수입니다. 30pt 이상으로 급등하면 극단적 패닉(공포 매수 기회), 15pt 이하의 장기 안정은 안도감 팽배(상투 경계) 구간을 의미합니다.",
        "line_color": "#FB923C",  # Orange
        "overbought": 30.0,       # 공포/패닉
        "oversold": 15.0,         # 안도/낙관
        "has_bands": True,
        "is_breadth": False,
    },
    "외인&기관수급": {
        "name": "외국인 & 기관 누적 순매수",
        "short_name": "외인/기관 누적순매수",
        "chart_label": "기간 누적 순매수 (조 원)",
        "unit": "조 원",
        "format": "{:+.1f}조 원",
        "desc": "한국 거래소 및 네이버 증권 공식 집계 기준의 외국인 및 기관 일별 순매수 실데이터를 바탕으로 산출된 '선택 조회 기간 누적 순매수'입니다. 조회 기간 시작일(0.0조 원)을 기준으로 기간 내 실제 자금 유입(+) 및 유출(-)을 정확히 추적하며, 외국인의 지속적인 순매도세와 기관의 방어 매수 흐름을 한눈에 파악할 수 있습니다.",
        "line_color": "#EF4444",      # Red
        "line_color_for": "#EF4444",  # Red (외국인)
        "line_color_inst": "#10B981", # Green (기관)
        "has_bands": False,
        "is_breadth": False,
    },
    "200일선상회": {
        "name": "200일선 상회 종목 비율 (% > 200-MA)",
        "short_name": "% > 200-MA",
        "chart_label": "상회 종목 비율 (%)",
        "unit": "%",
        "format": "{:.1f}%",
        "desc": "시장 전체 상장 종목 중 현재 주가가 200일 장기 이동평균선 위에 위치한 종목의 백분율입니다. 75% 이상은 시장 전반의 과열(상투 경계), 25% 이하는 시장 전체의 극단적 투매(바닥 형성)를 나타냅니다.",
        "line_color": "#E879F9",  # Fuchsia / Magenta (지수 하늘색과 뚜렷이 대비되는 네온 핑크-퍼플)
        "overbought": 75.0,
        "oversold": 25.0,
        "midline": 50.0,
        "has_bands": True,
        "is_breadth": True,
    },
}

# 가이드 03: 고대비 Tailwind Slate 액자형 카드 표준 테마
STANDARD_CHART_THEME = {
    'paper_bgcolor': '#1E293B',    # Tailwind Slate-800 (외곽 카드 배경)
    'plot_bgcolor': '#0F172A',     # Tailwind Slate-900 (내부 딥 블랙 플롯)
    'text_main': '#F8FAFC',        # 타이틀/헤더 텍스트 (순백색)
    'text_body': '#E2E8F0',        # 본문 및 축 라벨 (부드러운 화이트)
    'text_muted': '#CBD5E1',       # 축 눈금 수치 텍스트 (Slate-300)
    'grid_color': '#334155',       # 그리드 격자선 (Slate-700)
    'border_color': '#475569',     # 축 기준선 (Slate-600)
    'legend_bg': 'rgba(30, 41, 59, 0.85)',
    'legend_border': '#334155',
    'hover_bg': 'rgba(15, 23, 42, 0.95)',
    'hover_border': '#475569'
}

# 지수 선 색상
INDEX_LINE_COLOR = "#38BDF8"  # Sky Blue 400
INDEX_FILL_COLOR = "rgba(56, 189, 248, 0.08)"

# 데이터 파일 경로
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FUNDAMENTALS_CACHE_PATH = os.path.join(DATA_DIR, "krx_fundamentals_cache.csv")
ADR_HISTORY_PATH = os.path.join(DATA_DIR, "krx_adr_history.csv")
PRICE_CACHE_PATH = os.path.join(DATA_DIR, "index_price_cache.csv")
EXTENDED_INDICATORS_PATH = os.path.join(DATA_DIR, "krx_extended_indicators.csv")
