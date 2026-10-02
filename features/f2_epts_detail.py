"""기능 2 — 등록된 EPTS 들여다보기

대책이 어떻게 작성됐는지(주제·배경·내용), 어떤 EPIC이 붙어 있는지
(매칭 / 포워딩 구분) 한 화면에서 확인한다.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core import transform
from core.loader import Bundle
from .base import Page, WIDE, download_button, link_column_config, metric_row, need


def _themes(row: pd.Series) -> pd.DataFrame:
    rows = []
    for i in (1, 2, 3):
        big, mid, sml = (row.get(f"테마_대분류{i}"), row.get(f"테마_중분류{i}"),
                         row.get(f"테마_소분류{i}"))
        if any(isinstance(v, str) and v.strip() for v in (big, mid, sml)):
            rows.append({"슬롯": i, "대분류": big, "중분류": mid, "소분류": sml})
    return pd.DataFrame(rows)


def render(bundle: Bundle) -> None:
    st.subheader("EPTS 대책 상세")
    st.caption("대책의 주제·배경·내용과, 연결된 EPIC 자료를 함께 봅니다.")

    if not need(bundle, "epts"):
        return

    epts = bundle.epts.copy()
    epts["CTE_SEQ"] = epts["CTE_SEQ"].astype(str)

    # ── 대책 찾기 ───────────────────────────────────────────────
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 1, 1])
        q = c1.text_input("대책명 검색", placeholder="예: 퇴직연금")
        use_y = c2.toggle("사용중(Y)만", value=True)
        linked = c3.selectbox("연결 상태", ["전체", "연결 있음", "연결 없음"])

    pool = epts
    if q.strip():
        pool = pool[pool["CTE_NM"].fillna("").str.contains(q.strip(), case=False)]
    if use_y and "CTE_USE_YN" in pool.columns:
        pool = pool[pool["CTE_USE_YN"] == "Y"]
    if linked != "전체" and "매칭_EPIC수" in pool.columns:
        total_link = (pd.to_numeric(pool["매칭_EPIC수"], errors="coerce").fillna(0)
                      + pd.to_numeric(pool.get("포워딩_EPIC수", 0), errors="coerce").fillna(0))
        pool = pool[total_link > 0] if linked == "연결 있음" else pool[total_link == 0]

    if pool.empty:
        st.info("조건에 맞는 대책이 없습니다.")
        return

    labels = (pool["CTE_SEQ"] + " · " + pool["CTE_NM"].fillna("(제목 없음)")).tolist()
    pick = st.selectbox(f"대책 선택 ({len(pool):,}건)", labels)
    row = pool.iloc[labels.index(pick)]

    st.divider()

    # ── 개요 ────────────────────────────────────────────────────
    st.markdown(f"### {row.get('CTE_NM') or '(제목 없음)'}")
    metric_row([
        ("대책 순번", row.get("CTE_SEQ")),
        ("사용 여부", row.get("CTE_USE_YN") or "-"),
        ("매칭 EPIC", row.get("매칭_EPIC수") or 0),
        ("포워딩 EPIC", row.get("포워딩_EPIC수") or 0),
        ("추진내역", row.get("추진내역_건수") or 0),
    ])

    info = {k: row.get(k) for k in
            ("발표일자", "소관부처_대", "소관부처_중", "등록일시", "수정일시")
            if row.get(k) is not None}
    if info:
        st.caption(" · ".join(f"**{k}** {v}" for k, v in info.items() if v))

    # ── 주제(테마) ──────────────────────────────────────────────
    th = _themes(row)
    if th.empty:
        st.warning("관련테마가 등록돼 있지 않습니다. 추천·매칭 정확도가 떨어집니다.")
    else:
        st.markdown("##### 관련 주제")
        st.dataframe(th, **WIDE, hide_index=True)

    # ── 배경 · 내용 ─────────────────────────────────────────────
    st.markdown("##### 작성 내용")
    tabs = st.tabs(["정책배경", "정책내용", "평가내용", "대책설명"])
    for tab, key in zip(tabs, ("정책배경", "정책내용", "평가내용", "대책설명")):
        with tab:
            val = row.get(key)
            if isinstance(val, str) and val.strip():
                st.markdown(val.replace("\n", "  \n"))
            else:
                st.caption("작성된 내용이 없습니다.")

    # ── 연결된 EPIC ─────────────────────────────────────────────
    st.markdown("##### 연결된 EPIC 자료")
    if bundle.link.empty or bundle.epic.empty:
        st.caption("link / epic 데이터가 없어 연결 목록을 표시할 수 없습니다.")
        return

    links = transform.epts_links(row["CTE_SEQ"], bundle.link, bundle.epic)
    if links.empty:
        st.info("연결된 자료가 없습니다. **추진내역 추천** 기능에서 후보를 찾아보세요.")
        return

    for rel in links["관계구분"].unique():
        sub = links[links["관계구분"] == rel].drop(columns=["관계구분"])
        st.markdown(f"**{rel}** · {len(sub):,}건")
        st.dataframe(sub, **WIDE, hide_index=True,
                     column_config=link_column_config(sub))
    download_button(links, f"대책_{row['CTE_SEQ']}_연결자료.csv")


PAGE = Page(
    key="f2",
    label="EPTS 대책 상세",
    icon="🔎",
    render=render,
    help="대책의 주제·배경·내용과 연결된 EPIC 확인",
)
