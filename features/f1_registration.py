"""기능 1 — EPTS 등록 현황

TOPIC에 P가 있는 EPIC 자료(= 등록 대상)가 실제로 대책(CTE)에 등록됐는지
부처별로 확인한다. 부처는 PUBLISHER1의 첫 토큰이다.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core import transform
from core.loader import Bundle
from .base import Page, WIDE, download_button, link_column_config, metric_row, need


def render(bundle: Bundle) -> None:
    st.subheader("EPTS 등록 현황")
    st.caption("TOPIC에 **P**가 있는 자료가 대책에 등록됐는지 부처별로 점검합니다. "
               "등록 판정은 대책 본체 매칭 기준이며, 포워딩만 있는 건은 미등록으로 봅니다.")

    if not need(bundle, "epic"):
        return

    epic = bundle.epic

    # ── 필터 ────────────────────────────────────────────────────
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        dates = epic["PUBLISH_DATE"].dropna().astype(str)
        lo, hi = (dates.min(), dates.max()) if not dates.empty else ("", "")
        period = c1.text_input("발간일자 범위 (YYYYMMDD)", value=f"{lo} ~ {hi}",
                               help="비워 두면 전체")
        only_p = c2.toggle("등록 대상(TOPIC=P)만", value=True)
        show_all = c3.toggle("전체 부처", value=True)

    df = epic.copy()
    if "~" in period:
        a, b = (x.strip() for x in period.split("~", 1))
        if a:
            df = df[df["PUBLISH_DATE"].astype(str) >= a]
        if b:
            df = df[df["PUBLISH_DATE"].astype(str) <= b]

    target = df[df["등록대상"]] if only_p else df
    if target.empty:
        st.info("조건에 맞는 자료가 없습니다.")
        return

    # ── 전체 지표 ───────────────────────────────────────────────
    total = target["NUM"].nunique()
    done = int(target["등록여부"].sum())
    rate = f"{done / total * 100:.1f}%" if total else "-"
    metric_row([("대상 자료", f"{total:,}"), ("등록", f"{done:,}"),
                ("미등록", f"{total - done:,}"), ("등록률", rate)])

    # ── 부처별 집계 ─────────────────────────────────────────────
    summary = transform.registration_by_ministry(target, only_target=False)
    st.markdown("##### 부처별 집계")
    st.caption("미등록이 많은 순입니다.")

    view = summary if show_all else summary.head(15)
    st.dataframe(
        view, **WIDE, hide_index=True,
        column_config={
            "등록률": st.column_config.ProgressColumn(
                "등록률", format="%.1f%%", min_value=0, max_value=100),
            "대상": st.column_config.NumberColumn("대상", format="%d"),
            "등록": st.column_config.NumberColumn("등록", format="%d"),
            "미등록": st.column_config.NumberColumn("미등록", format="%d"),
        },
    )
    download_button(summary, "등록현황_부처별.csv", "부처별 집계 내려받기")

    # ── 부처 선택 → 자료 목록 ──────────────────────────────────
    st.markdown("##### 자료 목록")
    picks = st.multiselect("부처", summary["부처"].dropna().tolist(),
                           placeholder="전체 부처")
    status = st.radio("상태", ["미등록만", "등록만", "전체"],
                      horizontal=True, index=0)

    detail = target
    if picks:
        detail = detail[detail["부처"].isin(picks)]
    if status == "미등록만":
        detail = detail[~detail["등록여부"]]
    elif status == "등록만":
        detail = detail[detail["등록여부"]]

    cols = [c for c in ["NUM", "PUBLISH_DATE", "부처", "TITLE",
                        "매핑대상_소분류1", "연결_대책목록", "URL"]
            if c in detail.columns]
    out = detail[cols].sort_values("PUBLISH_DATE", ascending=False,
                                   ignore_index=True)
    st.caption(f"{len(out):,}건")
    st.dataframe(out, **WIDE, hide_index=True,
                 column_config=link_column_config(out), height=420)
    download_button(out, f"등록현황_{status}.csv")


PAGE = Page(
    key="f1",
    label="EPTS 등록 현황",
    icon="📋",
    render=render,
    help="TOPIC=P 자료의 대책 등록 여부를 부처별로 점검",
)
