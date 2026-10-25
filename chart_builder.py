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
    **kwargs
) -> go.Figure:
    """
    주가지수와 선택된 보조지표를 단일 프레임에서 이중 Y축으로 합성한 고대비 차트를 생성합니다.
    - use_log_scale: True일 경우 좌측 주가지수 Y축을 로그 스케일(Logarithmic Scale)로 렌더링
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

    # 2. 주가지수 트레이스 (좌측 Primary Y축)
    trace_market_name = f"{market_name} 지수" + (" (Log)" if use_log_scale else "")
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["close"],
            name=trace_market_name,
            mode="lines",
            line=dict(color=INDEX_LINE_COLOR, width=2.2),
            hovertemplate=f"{market_name} 종가: " + "%{y:,.2f}pt<extra></extra>",
        ),
        secondary_y=False,
    )

    # 3. 보조지표 트레이스 (우측 Secondary Y축)
    if indicator_name == "PER":
        per_series = df["per"].dropna()
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["per"],
                name="PER",
                mode="lines",
                line=dict(color=meta.get("line_color", "#F59E0B"), width=2.0),
                hovertemplate="PER: %{y:.2f}배<extra></extra>",
            ),
            secondary_y=True,
        )
        # 기간 평균선
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
        pbr_series = df["pbr"].dropna()
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["pbr"],
                name="PBR",
                mode="lines",
                line=dict(color=meta.get("line_color", "#10B981"), width=2.0),
                hovertemplate="PBR: %{y:.2f}배<extra></extra>",
            ),
            secondary_y=True,
        )
        # 기간 평균선
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
    chart_title_text = f"<b>{market_name} 지수 & {chart_indicator_label} 비교 차트{scale_label}</b>"

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
        height=520,
    )

    # 6. X축 설정 (날짜 포맷 정규화)
    fig.update_xaxes(
        gridcolor=STANDARD_CHART_THEME['grid_color'],
        linecolor=STANDARD_CHART_THEME['border_color'],
        tickfont=dict(color=STANDARD_CHART_THEME['text_muted'], size=11),
        tickformat="%Y-%m-%d",
        hoverformat="%Y-%m-%d",
    )

    # 7. 좌측 Y축 (주가지수)
    y1_title = f"<b>{market_name} 지수 (Log, pt)</b>" if use_log_scale else f"<b>{market_name} 지수 (pt)</b>"
    y1_type = "log" if use_log_scale else "linear"

    # 유효한 주가지수 범위 산출 (로그 스케일 시 명시적 range 지정으로 Plotly 지수 폭발 버그 원천 차단)
    valid_close = df["close"].dropna()
    valid_close = valid_close[valid_close > 0]
    if use_log_scale and not valid_close.empty:
        min_p = float(valid_close.min())
        max_p = float(valid_close.max())
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
