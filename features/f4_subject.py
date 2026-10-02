"""기능 4 — 주제분류 현황

EIEC 주제 체계와 EPTS 테마 체계를 각각 보고, 둘 사이 매핑이
얼마나 채워져 있는지 점검한다.

매칭·집계는 코드로 하고, 화면에는 반드시 한글명을 함께 띄운다.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core import subject as subj
from core.loader import Bundle
from .base import WIDE, Page, download_button, metric_row, need


def _code_name(df: pd.DataFrame, code: str, name: str) -> pd.Series:
    """표에 넣을 '코드 · 한글명' 표기"""
    return df[code].astype(str) + " · " + df[name].fillna("(이름 없음)").astype(str)


def render(bundle: Bundle) -> None:
    st.subheader("주제분류 현황")
    st.caption("EIEC 주제와 EPTS 테마는 **서로 독립된 체계**입니다. "
               "둘을 잇는 건 `EPTS_RELATION` 매핑 하나뿐입니다. "
               "집계는 코드로 하고 표시는 한글명으로 합니다.")

    if not need(bundle, "subject_eiec", "subject_epts"):
        return

    eiec, epts_th, smap = (bundle.subject_eiec, bundle.subject_epts,
                           bundle.subject_map)

    usage = subj.epic_subject_usage(bundle.epic, eiec)
    theme_usage = subj.epts_theme_usage(bundle.epts, epts_th)

    # ── 요약 ────────────────────────────────────────────────────
    cov = subj.mapping_coverage(eiec, smap, bundle.epic)
    if cov:
        metric_row([("EIEC 주제", f"{cov['전체 주제']:,}"),
                    ("매핑됨", f"{cov['매핑됨']:,}"),
                    ("미매핑", f"{cov['미매핑']:,}"),
                    ("매핑률", f"{cov['매핑률']}%"),
                    ("EPTS 테마", f"{len(epts_th):,}")])
        if cov.get("미매핑 주제의 자료"):
            st.caption(f"미매핑 주제에 걸린 자료 {cov['미매핑 주제의 자료']:,}건 — "
                       "이 자료들은 주제코드로는 대책 후보를 찾을 수 없습니다.")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["매핑 현황", "EIEC 주제 체계", "EPTS 테마 체계", "정합성 점검"])

    # ── 탭1 매핑 현황 ───────────────────────────────────────────
    with tab1:
        if smap.empty:
            st.warning("`subject_map` 데이터가 없습니다. `06_subject_map.sql` 결과를 올려 주세요.")
        else:
            left, right = st.columns(2)
            level = left.selectbox("매핑 단계", ["소분류", "중분류", "대분류"])
            right.caption(" ")

            pairs = subj.mapping_pairs(smap, level)
            st.markdown(f"**{level} 매핑** · {len(pairs):,}쌍 "
                        f"(주제 {pairs['주제코드'].nunique():,}종 → "
                        f"테마 {pairs['테마코드'].nunique():,}종)")
            st.dataframe(pairs, **WIDE, hide_index=True, height=320)
            download_button(pairs, f"주제매핑_{level}.csv")

        st.markdown("##### 미매핑 EIEC 주제")
        st.caption("EPTS 테마에 연결되지 않은 주제입니다. 자료가 많은 순으로 보여 "
                   "우선순위를 판단할 수 있습니다.")
        un = subj.unmapped_subjects(eiec, smap, usage)
        if un.empty:
            st.success("모든 주제가 매핑돼 있습니다.")
        else:
            st.dataframe(un, **WIDE, hide_index=True, height=300)
            download_button(un, "미매핑_주제.csv")

    # ── 탭2 EIEC 주제 체계 ──────────────────────────────────────
    with tab2:
        st.caption("⚠ EIEC 주제는 마스터에 부모 컬럼이 없어 **코드 자리수로 계층을 추정**했습니다 "
                   "(`C` / `C05` / `C0501`). 실제 체계와 다르면 알려 주세요.")
        if usage.empty:
            st.info("데이터가 없습니다.")
        else:
            c1, c2 = st.columns([1, 2])
            bigs = sorted(usage["대분류코드"].dropna().unique()) \
                if "대분류코드" in usage.columns else []
            pick_big = c1.multiselect("대분류 코드", bigs, placeholder="전체")
            only_used = c2.toggle("자료가 있는 주제만", value=False)

            view = usage
            if pick_big:
                view = view[view["대분류코드"].isin(pick_big)]
            if only_used and "자료수" in view.columns:
                view = view[view["자료수"] > 0]

            cols = [c for c in ["주제코드", "주제명", "대분류코드", "중분류코드",
                                "중분류명", "자료수", "등록대상수", "매핑여부"]
                    if c in view.columns]
            view = view[cols].sort_values(
                "자료수" if "자료수" in cols else "주제코드",
                ascending=False, ignore_index=True)
            st.caption(f"{len(view):,}종")
            st.dataframe(view, **WIDE, hide_index=True, height=420,
                         column_config={"자료수": st.column_config.NumberColumn(format="%d"),
                                        "등록대상수": st.column_config.NumberColumn(format="%d")})
            download_button(view, "EIEC_주제체계.csv")

    # ── 탭3 EPTS 테마 체계 ──────────────────────────────────────
    with tab3:
        if theme_usage.empty:
            st.info("데이터가 없습니다.")
        else:
            c1, c2 = st.columns([2, 1])
            depths = sorted(pd.to_numeric(theme_usage["깊이"],
                                          errors="coerce").dropna().unique())
            pick_d = c1.multiselect("계층 깊이", [int(d) for d in depths],
                                    placeholder="전체")
            only_y = c2.toggle("사용중(Y)만", value=True)

            view = theme_usage
            if pick_d:
                view = view[pd.to_numeric(view["깊이"], errors="coerce").isin(pick_d)]
            if only_y and "사용여부" in view.columns:
                view = view[view["사용여부"] == "Y"]

            cols = [c for c in ["테마코드", "테마명", "계층", "대분류명", "중분류명",
                                "대책수", "사용여부", "이름경로"] if c in view.columns]
            view = view[cols].reset_index(drop=True)
            st.caption(f"{len(view):,}종")
            st.dataframe(view, **WIDE, hide_index=True, height=420)
            download_button(view, "EPTS_테마체계.csv")

            st.markdown("##### 쓰이지 않는 테마")
            st.caption("어떤 EIEC 주제도 가리키지 않는 소분류 테마입니다.")
            unused = subj.unused_themes(theme_usage, smap)
            if unused.empty:
                st.success("모든 소분류 테마가 매핑돼 있습니다.")
            else:
                st.dataframe(unused, **WIDE, hide_index=True, height=260)
                download_button(unused, "미사용_테마.csv")

    # ── 탭4 정합성 점검 ─────────────────────────────────────────
    with tab4:
        st.caption("코드 기준으로만 잡히는 문제들입니다. 이름으로는 드러나지 않습니다.")

        st.markdown("##### 마스터에 없는 주제코드")
        orphan = subj.orphan_subject_codes(bundle.epic, eiec)
        if orphan.empty:
            st.success("자료의 주제코드가 모두 마스터에 있습니다.")
        else:
            st.warning(f"{len(orphan):,}종이 마스터에 없습니다. 폐지된 코드이거나 입력 오류입니다.")
            st.dataframe(orphan, **WIDE, hide_index=True)
            download_button(orphan, "미등록_주제코드.csv")

        st.markdown("##### 깨진 매핑")
        broken = subj.broken_mappings(smap)
        if broken.empty:
            st.success("매핑의 양쪽 코드가 모두 마스터에 존재합니다.")
        else:
            st.warning(f"{len(broken):,}건이 존재하지 않는 코드를 가리킵니다.")
            st.dataframe(broken, **WIDE, hide_index=True)
            download_button(broken, "깨진_매핑.csv")


PAGE = Page(
    key="f4",
    label="주제분류 현황",
    icon="🗂️",
    render=render,
    help="EIEC 주제 ↔ EPTS 테마 체계와 매핑 점검",
)
