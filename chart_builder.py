"""
chart_builder.py
Market Balance 대시보드의 합성 차트(Dual-Axis Plotly Chart) 생성 모듈.
- 00 App_AI_Template [가이드 03] 차트 Plotly 디자인 표준 100% 준수
- 고대비 Tailwind Slate 액자형 카드 표준 테마 (paper #1E293B / plot #0F172A)
- 지수와 보조지표를 하나의 프레임에서 직관적으로 비교하는 이중 Y축(Secondary Y) 구조
- RSI(20) 과매수(70)/과매도(30) 기준선 및 ADR(14)/ADR(1) 3중 합성 차트 지원
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

from config import (
    STANDARD_CHART_THEME,
    INDEX_LINE_COLOR,
    INDICATOR_META
)


def create_market_balance_chart(
    df: pd.DataFrame,
    market_name: str,
    indicator_name: str,
    use_log_scale: bool = False,
    show_ma_lines: bool = False,
    show_bb_bands: bool = True,
    **kwargs
) -> go.Figure:
    """
    주가지수(일봉 캔들차트 + 볼린저밴드/이평선)와 선택된 보조지표를 단일 프레임에서 이중 Y축으로 합성한 고대비 차트를 생성합니다.
    - use_log_scale: True일 경우 좌측 주가지수 Y축을 로그 스케일(Logarithmic Scale)로 렌더링
    - show_ma_lines: True일 경우 5, 20, 60, 120일 이동평균선을 좌측 Y축에 함께 오버레이
    - show_bb_bands: True일 경우 20일 기준 볼린저밴드(상단, 중심선, 하단 음영 밴드) 오버레이
    """
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=STANDARD_CHART_THEME['paper_bgcolor'],
            plot_bgcolor=STANDARD_CHART_THEME['plot_bgcolor'],
            annotations=[dict(
                text="표시할 데이터가 없습니다.",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color=STANDARD_CHART_THEME['text_muted'])
            )]
        )
        return fig

    meta = INDICATOR_META.get(indicator_name, {})
    chart_indicator_label = meta.get("chart_label", indicator_name)

    # 1. 이중 Y축 서브플롯 생성
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 2. 주가지수 일봉 캔들차트 트레이스 (좌측 Primary Y축)
    trace_market_name = f"{market_name} 일봉" + (" (Log)" if use_log_scale else "")
    c_open = df["open"] if "open" in df.columns else df["close"]
    c_high = df["high"] if "high" in df.columns else df["close"]
    c_low = df["low"] if "low" in df.columns else df["close"]
    c_close = df["close"]

    fig.add_trace(
        go.Candlestick(
            x=df["date"],
            open=c_open,
            high=c_high,
            low=c_low,
            close=c_close,
            name=trace_market_name,
            increasing_line_color="#EF4444",      # 한국 증시 표준 양봉 (Red)
            increasing_fillcolor="#EF4444",
            decreasing_line_color="#3B82F6",      # 한국 증시 표준 음봉 (Blue)
            decreasing_fillcolor="#3B82F6",
            whiskerwidth=0.8,
            hovertemplate="시 %{open:,.2f} | 고 %{high:,.2f} | 저 %{low:,.2f} | 종 %{close:,.2f}<extra></extra>",
            showlegend=True,
        ),
        secondary_y=False,
    )

    # 2.5. 볼린저밴드 트레이스 (20, 2)
    if show_bb_bands and "bb_upper" in df.columns and "bb_lower" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["bb_upper"],
                name="BB 상단 (20, 2)",
                mode="lines",
                line=dict(color="rgba(148, 163, 184, 0.45)", width=1.1, dash="dash"),
                hovertemplate="BB 상단: %{y:,.2f}pt<extra></extra>",
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["bb_lower"],
                name="BB 하단 (20, 2)",
                mode="lines",
                line=dict(color="rgba(148, 163, 184, 0.45)", width=1.1, dash="dash"),
                fill="tonexty",
                fillcolor="rgba(148, 163, 184, 0.08)",
                hovertemplate="BB 하단: %{y:,.2f}pt<extra></extra>",
            ),
            secondary_y=False,
        )
        if "bb_mid" in df.columns and not show_ma_lines:
            fig.add_trace(
                go.Scatter(
                    x=df["date"],
                    y=df["bb_mid"],
                    name="BB 중심선 (20MA)",
                    mode="lines",
                    line=dict(color="rgba(245, 158, 11, 0.65)", width=1.1, dash="dot"),
                    hovertemplate="BB 중심선: %{y:,.2f}pt<extra></extra>",
                ),
                secondary_y=False,
            )

    # 3. 이동평균선 트레이스 (5, 20, 60, 120일선)
    if show_ma_lines:
        ma_configs = [
            ("ma5", "5일선", "#F59E0B", 1.2),     # Amber / Gold (단기)
            ("ma20", "20일선", "#FB7185", 1.3),   # Rose / Pink (생명선)
            ("ma60", "60일선", "#06B6D4", 1.3),   # Cyan (수급선)
            ("ma120", "120일선", "#A855F7", 1.3), # Purple (경기선)
        ]
        for col, label, color, width in ma_configs:
            if col in df.columns and df[col].notna().any():
                fig.add_trace(
                    go.Scatter(
                        x=df["date"],
                        y=df[col],
                        name=label,
                        mode="lines",
                        line=dict(color=color, width=width),
                        hovertemplate=f"{label}: %{{y:,.2f}}pt<extra></extra>",
                    ),
                    secondary_y=False,
                )

    # 4. 보조지표 트레이스 (우측 Secondary Y축)
    if indicator_name == "PER":
        # 0.00 이하 또는 NaN은 KRX 미집계 상태이므로 필터링하여 유효한 공시 데이터만 플롯 (0으로 곤두박질 방지)
        valid_per_df = df[pd.notna(df["per"]) & (df["per"] > 0.01)]
        per_series = valid_per_df["per"]
        fig.add_trace(
            go.Scatter(
                x=valid_per_df["date"],
                y=valid_per_df["per"],
                name="PER",
                mode="lines",
                line=dict(color=meta.get("line_color", "#F59E0B"), width=2.0),
                hovertemplate="PER: %{y:.2f}배<extra></extra>",
                connectgaps=True,
            ),
            secondary_y=True,
        )
        # 기간 평균선 (유효한 공시 데이터 기준으로만 계산)
        if not per_series.empty:
            mean_per = per_series.mean()
            fig.add_hline(
                y=mean_per,
                line_dash="dot",
                line_color="rgba(245, 158, 11, 0.6)",
                line_width=1.2,
                annotation_text=f"기간 평균 PER: {mean_per:.2f}배",
                annotation_position="top right",
                annotation_font=dict(color="#FCD34D", size=10),
                secondary_y=True,
            )

    elif indicator_name == "PBR":
        # 0.00 이하 또는 NaN은 KRX 미집계 상태이므로 필터링하여 유효한 공시 데이터만 플롯 (0으로 곤두박질 방지)
        valid_pbr_df = df[pd.notna(df["pbr"]) & (df["pbr"] > 0.01)]
        pbr_series = valid_pbr_df["pbr"]
        fig.add_trace(
            go.Scatter(
                x=valid_pbr_df["date"],
                y=valid_pbr_df["pbr"],
                name="PBR",
                mode="lines",
                line=dict(color=meta.get("line_color", "#10B981"), width=2.0),
                hovertemplate="PBR: %{y:.2f}배<extra></extra>",
                connectgaps=True,
            ),
            secondary_y=True,
        )
        # 기간 평균선 (유효한 공시 데이터 기준으로만 계산)
        if not pbr_series.empty:
            mean_pbr = pbr_series.mean()
            fig.add_hline(
                y=mean_pbr,
                line_dash="dot",
                line_color="rgba(16, 185, 129, 0.6)",
                line_width=1.2,
                annotation_text=f"기간 평균 PBR: {mean_pbr:.2f}배",
                annotation_position="top right",
                annotation_font=dict(color="#6EE7B7", size=10),
                secondary_y=True,
            )

    elif indicator_name == "RSI":
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["rsi_20"],
                name="RSI(20)",
                mode="lines",
                line=dict(color=meta.get("line_color", "#8B5CF6"), width=2.0),
                hovertemplate="RSI(20): %{y:.1f}<extra></extra>",
            ),
            secondary_y=True,
        )
        # 과매수(70) 기준선
        fig.add_hline(
            y=70,
            line_dash="dash",
            line_color="rgba(248, 113, 113, 0.7)",
            line_width=1.2,
            annotation_text="과매수 (70)",
            annotation_position="top left",
            annotation_font=dict(color="#F87171", size=10),
            secondary_y=True,
        )
        # 과매도(30) 기준선
        fig.add_hline(
            y=30,
            line_dash="dash",
            line_color="rgba(52, 211, 153, 0.7)",
            line_width=1.2,
            annotation_text="과매도 (30)",
            annotation_position="bottom left",
            annotation_font=dict(color="#34D399", size=10),
            secondary_y=True,
        )
        # 중심선(50)
        fig.add_hline(
            y=50,
            line_dash="dot",
            line_color="rgba(148, 163, 184, 0.4)",
            line_width=1.0,
            secondary_y=True,
        )

    elif indicator_name == "MACD":
        if "macd" in df.columns:
            # 1. Oscillator (Histogram Bar)
            if "macd_osc" in df.columns:
                osc_colors = [
                    meta.get("osc_pos_color", "rgba(239, 68, 68, 0.50)") if (pd.notna(val) and val >= 0)
                    else meta.get("osc_neg_color", "rgba(59, 130, 246, 0.50)")
                    for val in df["macd_osc"]
                ]
                fig.add_trace(
                    go.Bar(
                        x=df["date"],
                        y=df["macd_osc"],
                        name="Oscillator",
                        marker=dict(color=osc_colors),
                        hovertemplate="Oscillator: %{y:+.2f}pt<extra></extra>",
                    ),
                    secondary_y=True,
                )

            # 2. MACD Line (12, 26)
            fig.add_trace(
                go.Scatter(
                    x=df["date"],
                    y=df["macd"],
                    name="MACD (12, 26)",
                    mode="lines",
                    line=dict(color=meta.get("line_color", "#38BDF8"), width=2.0),
                    hovertemplate="MACD: %{y:+.2f}pt<extra></extra>",
                ),
                secondary_y=True,
            )

            # 3. Signal Line (9)
            if "macd_signal" in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df["date"],
                        y=df["macd_signal"],
                        name="Signal (9)",
                        mode="lines",
                        line=dict(color=meta.get("signal_color", "#FB7185"), width=1.5, dash="dot"),
                        hovertemplate="Signal: %{y:+.2f}pt<extra></extra>",
                    ),
                    secondary_y=True,
                )

            # 4. Zero Line 기준선
            fig.add_hline(
                y=0,
                line_dash="dash",
                line_color="rgba(148, 163, 184, 0.45)",
                line_width=1.0,
                annotation_text="기준선 (0)",
                annotation_position="bottom right",
                annotation_font=dict(color="#94A3B8", size=9),
                secondary_y=True,
            )

    elif indicator_name == "ADR":
        # ADR(14): 14거래일 누적 등락비율 (핵심 추세선)
        # 당일 ADR(1)의 극단적 일별 스파이크로 인한 Y축 왜곡을 방지하기 위해 차트 선은 ADR(14)만 단독 표시하고,
        # 당일 ADR(1) 수치는 호버 툴팁 및 상단 KPI 카드에 온전히 보존
        if "adr_14" in df.columns:
            has_adr1 = "adr_1" in df.columns
            hover_tmpl = "<b>ADR(14): %{y:.1f}%</b>" + (" (당일 ADR: %{customdata:.1f}%)" if has_adr1 else "") + "<extra></extra>"
            fig.add_trace(
                go.Scatter(
                    x=df["date"],
                    y=df["adr_14"],
                    customdata=df["adr_1"] if has_adr1 else None,
                    name="ADR(14)",
                    mode="lines",
                    line=dict(color=meta.get("line_color_14", "#EC4899"), width=2.4),
                    hovertemplate=hover_tmpl,
                ),
                secondary_y=True,
            )

        # ADR 기준선들
        # 과열권 (120%)
        fig.add_hline(
            y=120,
            line_dash="dash",
            line_color="rgba(248, 113, 113, 0.7)",
            line_width=1.2,
            annotation_text="과열권 (120%)",
            annotation_position="top left",
            annotation_font=dict(color="#F87171", size=10),
            secondary_y=True,
        )
        # 바닥권/과매도 (75%)
        fig.add_hline(
            y=75,
            line_dash="dash",
            line_color="rgba(52, 211, 153, 0.7)",
            line_width=1.2,
            annotation_text="바닥권 (75%)",
            annotation_position="bottom left",
            annotation_font=dict(color="#34D399", size=10),
            secondary_y=True,
        )
        # 균형 기준선 (100%)
        fig.add_hline(
            y=100,
            line_dash="dot",
            line_color="rgba(148, 163, 184, 0.4)",
            line_width=1.0,
            annotation_text="균형선 (100%)",
            annotation_position="bottom right",
            annotation_font=dict(color="#94A3B8", size=9),
            secondary_y=True,
        )

    elif indicator_name == "예탁금&신용":
        # 1. 고객예탁금
        if "deposit_jo" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["date"],
                    y=df["deposit_jo"],
                    name="고객예탁금 (조 원)",
                    mode="lines",
                    line=dict(color=meta.get("line_color_dep", "#F59E0B"), width=2.0),
                    hovertemplate="고객예탁금: %{y:.1f}조 원<extra></extra>",
                ),
                secondary_y=True,
            )
        # 2. 신용잔고
        if "credit_jo" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["date"],
                    y=df["credit_jo"],
                    name="신용잔고 (조 원)",
                    mode="lines",
                    line=dict(color=meta.get("line_color_cred", "#F43F5E"), width=2.0),
                    hovertemplate="신용잔고: %{y:.1f}조 원<extra></extra>",
                ),
                secondary_y=True,
            )

    elif indicator_name == "VKOSPI":
        if "vkospi" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["date"],
                    y=df["vkospi"],
                    name="VKOSPI",
                    mode="lines",
                    line=dict(color=meta.get("line_color", "#FB923C"), width=2.2),
                    hovertemplate="VKOSPI: %{y:.2f}pt<extra></extra>",
                ),
                secondary_y=True,
            )
            # 패닉/공포 기준선 (30)
            fig.add_hline(
                y=30,
                line_dash="dash",
                line_color="rgba(248, 113, 113, 0.7)",
                line_width=1.2,
                annotation_text="패닉/공포 (30)",
                annotation_position="top left",
                annotation_font=dict(color="#F87171", size=10),
                secondary_y=True,
            )
            # 안도/낙관 기준선 (15)
            fig.add_hline(
                y=15,
                line_dash="dash",
                line_color="rgba(52, 211, 153, 0.7)",
                line_width=1.2,
                annotation_text="안도/낙관 (15)",
                annotation_position="bottom left",
                annotation_font=dict(color="#34D399", size=10),
                secondary_y=True,
            )

    elif indicator_name == "외인&기관수급":
        has_for_daily = "foreign_daily_eok" in df.columns
        has_inst_daily = "inst_daily_eok" in df.columns

        if "foreign_cum_jo" in df.columns:
            for_hover = "<b>외국인 누적: %{y:+.1f}조 원</b> (당일: %{customdata:+,.0f}억 원)<extra></extra>" if has_for_daily else "외국인 누적: %{y:+.1f}조 원<extra></extra>"
            fig.add_trace(
                go.Scatter(
                    x=df["date"],
                    y=df["foreign_cum_jo"],
                    customdata=df["foreign_daily_eok"] if has_for_daily else None,
                    name="외국인 누적순매수 (조 원)",
                    mode="lines",
                    line=dict(color=meta.get("line_color_for", "#EF4444"), width=2.2),
                    hovertemplate=for_hover,
                ),
                secondary_y=True,
            )
        if "inst_cum_jo" in df.columns:
            inst_hover = "<b>기관 누적: %{y:+.1f}조 원</b> (당일: %{customdata:+,.0f}억 원)<extra></extra>" if has_inst_daily else "기관 누적: %{y:+.1f}조 원<extra></extra>"
            fig.add_trace(
                go.Scatter(
                    x=df["date"],
                    y=df["inst_cum_jo"],
                    customdata=df["inst_daily_eok"] if has_inst_daily else None,
                    name="기관 누적순매수 (조 원)",
                    mode="lines",
                    line=dict(color=meta.get("line_color_inst", "#10B981"), width=2.0),
                    hovertemplate=inst_hover,
                ),
                secondary_y=True,
            )
        # 0선 기준선 (순매수 / 순매도 분기점)
        fig.add_hline(
            y=0,
            line_dash="dot",
            line_color="rgba(148, 163, 184, 0.55)",
            line_width=1.2,
            annotation_text="기준선 (0조)",
            annotation_position="bottom right",
            annotation_font=dict(color="#94A3B8", size=9),
            secondary_y=True,
        )

    elif indicator_name == "200일선상회":
        if "above_200ma" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["date"],
                    y=df["above_200ma"],
                    name="200일선 상회 비율 (%)",
                    mode="lines",
                    line=dict(color=meta.get("line_color", "#E879F9"), width=2.2),
                    hovertemplate="상회 비율: %{y:.1f}%<extra></extra>",
                ),
                secondary_y=True,
            )
            # 과열권 기준선 (75%)
            fig.add_hline(
                y=75,
                line_dash="dash",
                line_color="rgba(248, 113, 113, 0.7)",
                line_width=1.2,
                annotation_text="과열권 (75%)",
                annotation_position="top left",
                annotation_font=dict(color="#F87171", size=10),
                secondary_y=True,
            )
            # 바닥권 기준선 (25%)
            fig.add_hline(
                y=25,
                line_dash="dash",
                line_color="rgba(52, 211, 153, 0.7)",
                line_width=1.2,
                annotation_text="바닥권 (25%)",
                annotation_position="bottom left",
                annotation_font=dict(color="#34D399", size=10),
                secondary_y=True,
            )
            # 균형선 (50%)
            fig.add_hline(
                y=50,
                line_dash="dot",
                line_color="rgba(148, 163, 184, 0.4)",
                line_width=1.0,
                secondary_y=True,
            )

    # 4. 차트 제목 생성
    scale_label = " [로그 스케일]" if use_log_scale else ""
    chart_title_text = f"<b>{market_name} 일봉 & {chart_indicator_label} 비교 차트{scale_label}</b>"

    # 5. [가이드 03] 표준 layout 설정
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=STANDARD_CHART_THEME['paper_bgcolor'],
        plot_bgcolor=STANDARD_CHART_THEME['plot_bgcolor'],
        title=dict(
            text=chart_title_text,
            font=dict(color=STANDARD_CHART_THEME['text_main'], size=15),
            x=0.5,
            xanchor="center"
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor=STANDARD_CHART_THEME['hover_bg'],
            bordercolor=STANDARD_CHART_THEME['hover_border'],
            font=dict(color="#FFFFFF", size=12)
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor=STANDARD_CHART_THEME['legend_bg'],
            bordercolor=STANDARD_CHART_THEME['legend_border'],
            borderwidth=1,
            font=dict(color=STANDARD_CHART_THEME['text_main'], size=11)
        ),
        margin=dict(l=45, r=50, t=75, b=40),
        height=540,
        bargap=0.15,
        barmode="relative",
    )

    # 6. X축 설정 (비거래일(주말, 공휴일) 완전 배제 및 범주형(category) 축 적용)
    # HTS/금융 차트 표준: 시장이 개장된 실제 거래일만 X축에 연속 배치하여 주말 및 공휴일 공백과 0값 표출을 원천 차단
    fig.update_xaxes(
        type="category",
        nticks=10,
        rangeslider=dict(visible=False),
        gridcolor=STANDARD_CHART_THEME['grid_color'],
        linecolor=STANDARD_CHART_THEME['border_color'],
        tickfont=dict(color=STANDARD_CHART_THEME['text_muted'], size=11),
    )

    # 7. 좌측 Y축 (주가지수 일봉)
    y1_title = f"<b>{market_name} 일봉 (Log, pt)</b>" if use_log_scale else f"<b>{market_name} 일봉 (pt)</b>"
    y1_type = "log" if use_log_scale else "linear"

    # 유효한 주가지수 범위 산출 (로그 스케일 시 명시적 range 지정으로 Plotly 지수 폭발 버그 원천 차단)
    valid_low = df["low"].dropna() if "low" in df.columns else df["close"].dropna()
    valid_low = valid_low[valid_low > 0]
    valid_high = df["high"].dropna() if "high" in df.columns else df["close"].dropna()
    valid_high = valid_high[valid_high > 0]

    if use_log_scale and not valid_low.empty:
        min_p = float(valid_low.min())
        max_p = float(valid_high.max())
        log_min = float(np.log10(min_p * 0.96))
        log_max = float(np.log10(max_p * 1.04))
        y1_range = [log_min, log_max]
    else:
        y1_range = None

    fig.update_yaxes(
        title=dict(
            text=y1_title,
            font=dict(color=INDEX_LINE_COLOR, size=12)
        ),
        type=y1_type,
        range=y1_range,
        gridcolor=STANDARD_CHART_THEME['grid_color'],
        linecolor=STANDARD_CHART_THEME['border_color'],
        tickfont=dict(color=STANDARD_CHART_THEME['text_muted'], size=11),
        tickformat=",.0f" if use_log_scale else ",.1f",
        secondary_y=False,
    )

    # 8. 우측 Y축 (보조지표)
    y2_title_color = meta.get("line_color", meta.get("line_color_14", "#F59E0B"))
    fig.update_yaxes(
        title=dict(
            text=f"<b>{chart_indicator_label}</b>",
            font=dict(color=y2_title_color, size=12)
        ),
        gridcolor="rgba(51, 65, 85, 0.3)",  # 살짝 옅은 격자선으로 혼선 방지
        linecolor=STANDARD_CHART_THEME['border_color'],
        tickfont=dict(color=STANDARD_CHART_THEME['text_muted'], size=11),
        secondary_y=True,
    )

    # RSI 범위 0~100 고정
    if indicator_name == "RSI":
        fig.update_yaxes(range=[0, 100], secondary_y=True)

    # 9. [Plotly 버그 방어] add_hline(secondary_y=True) 호출 시 생성된 annotation의 yref가
    # Plotly 내부 결함으로 인해 'y'(Primary Y축)로 잘못 지정되는 현상 원천 교정
    # (이를 방치하면 yaxis가 log일 때 yref='y'에 걸린 PER 수치 20이 지수 축의 승수로 오인되어 10^20 폭발 발생)
    if fig.layout.annotations:
        for ann in fig.layout.annotations:
            if ann.yref == "y":
                ann.yref = "y2"

    return fig
