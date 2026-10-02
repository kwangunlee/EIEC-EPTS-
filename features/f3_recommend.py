"""기능 3 — 추진내역(EPIC 포워딩) 추천

대책의 제목·배경·내용을 질의로 삼아, 붙을 만한 EPIC 자료를 추천한다.
판단은 사람이 한다. 여기서는 후보와 근거만 제시한다.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core import recommend as reco
from core.loader import Bundle
from .base import Page, WIDE, download_button, link_column_config, need


def render(bundle: Bundle) -> None:
    st.subheader("추진내역 추천")
    st.caption("대책 내용과 EPIC 제목·초록을 대조해 **연결 후보**를 제시합니다. "
               "최종 판단은 담당자가 합니다.")

    if not need(bundle, "epts", "epic"):
        return

    epts = bundle.epts.copy()
    epts["CTE_SEQ"] = epts["CTE_SEQ"].astype(str)
    if "CTE_USE_YN" in epts.columns:
        epts = epts[epts["CTE_USE_YN"] == "Y"]
    if epts.empty:
        st.info("사용중인 대책이 없습니다.")
        return

    labels = (epts["CTE_SEQ"] + " · " + epts["CTE_NM"].fillna("(제목 없음)")).tolist()
    pick = st.selectbox(f"대책 선택 ({len(epts):,}건)", labels)
    row = epts.iloc[labels.index(pick)]

    with st.expander("추천 설정", expanded=False):
        c1, c2 = st.columns(2)
        cfg = reco.RecoConfig(
            top_n=c1.slider("추천 건수", 5, 100, 20, step=5),
            min_score=c1.slider("최소 점수", 0.0, 5.0, 0.3, step=0.1),
            only_topic_p=c2.toggle("등록 대상(TOPIC=P)만 후보로", value=True),
            exclude_linked=c2.toggle("이미 연결된 자료 제외", value=True),
        )
        st.caption(
            "점수 = 소분류 일치 ×%.1f + 중분류 ×%.1f + 대분류 ×%.1f + 키워드 유사도 ×%.1f"
            % (reco.WEIGHTS["소분류"], reco.WEIGHTS["중분류"],
               reco.WEIGHTS["대분류"], reco.WEIGHTS["키워드"])
        )

    themes = [row.get(f"테마_소분류{i}") for i in (1, 2, 3)]
    themes = [t for t in themes if isinstance(t, str) and t.strip()]
    if themes:
        st.caption("기준 소분류: " + ", ".join(themes))
    else:
        st.warning("이 대책에는 관련테마 소분류가 없어 **키워드만으로** 추천합니다. "
                   "정확도가 낮을 수 있습니다.")

    with st.spinner("후보 탐색 중…"):
        result = reco.recommend(row, bundle.epic, bundle.link, cfg)

    if result.empty:
        st.info("조건을 만족하는 후보가 없습니다. 최소 점수를 낮춰 보세요.")
        return

    st.markdown(f"##### 추천 결과 {len(result):,}건")
    st.dataframe(
        result, **WIDE, hide_index=True, height=460,
        column_config={
            **link_column_config(result),
            "점수": st.column_config.NumberColumn("점수", format="%.2f"),
            "유사도": st.column_config.ProgressColumn(
                "키워드", format="%.2f", min_value=0, max_value=1),
            "근거": st.column_config.TextColumn("근거", width="medium"),
        },
    )
    download_button(result, f"추천_{row['CTE_SEQ']}.csv")

    st.caption("점수가 3 이상이면 소분류가 일치하는 건으로, 우선 검토 대상입니다.")


PAGE = Page(
    key="f3",
    label="추진내역 추천",
    icon="🧭",
    render=render,
    help="대책에 붙을 만한 EPIC 자료를 추천",
)
