"""파생 컬럼·집계 — 원천 데이터에 업무 의미를 붙이는 계층.

여기 있는 함수는 전부 순수 함수(입력 DataFrame → 출력 DataFrame)다.
Streamlit에 의존하지 않으므로 그대로 테스트할 수 있다.
"""
from __future__ import annotations

import re

import pandas as pd

from . import schema

# 부처명 뒤에 붙는 하위 조직 접미사 — 첫 토큰이 부처가 아닐 때 탐지용
_ORG_TAIL = re.compile(r"(실|국|관|과|팀|단|원|처|청|부|위원회|본부)$")

# EIEC 상세페이지. NUM만 있으면 링크를 만들 수 있다.
EIEC_VIEW_URL = "https://eiec.kdi.re.kr/policy/materialView.do?num="


def extract_ministry(publisher: str | None) -> str | None:
    """PUBLISHER1의 첫 토큰을 부처로 뽑는다.

    '과학기술정보통신부 연구개발정책실 미래인재정책국 미래인재정책과'
      → '과학기술정보통신부'
    """
    if not isinstance(publisher, str):
        return None
    head = publisher.strip().split()
    if not head:
        return None
    return head[0]


def has_topic(topic: str | None, code: str = "P") -> bool:
    """TOPIC 문자열(쉼표 연결)에 해당 코드가 있는지.

    TOPIC에는 소문자 혼입(알려진 p 이슈)이 있어 대소문자를 무시한다.
    """
    if not isinstance(topic, str):
        return False
    return code.upper() in {t.strip().upper() for t in topic.split(",") if t.strip()}


def enrich_epic(epic: pd.DataFrame) -> pd.DataFrame:
    """EPIC에 업무 파생 컬럼을 붙인다 — 부처, 등록대상 여부."""
    out = epic.copy()
    if "PUBLISHER1" in out.columns:
        out["부처"] = out["PUBLISHER1"].map(extract_ministry)
    if "TOPIC" in out.columns:
        out["등록대상"] = out["TOPIC"].map(lambda v: has_topic(v, "P"))
    else:
        out["등록대상"] = False
    return out


def attach_link_status(epic: pd.DataFrame, link: pd.DataFrame) -> pd.DataFrame:
    """EPIC에 대책 연결 현황을 붙인다 — 등록여부, 연결 대책 목록·건수.

    link는 NUM × CTE_SEQ × 관계구분 형태라 NUM 단위로 집계해서 붙인다.
    (행 증식 없음)
    """
    out = epic.copy()
    if link is None or link.empty:
        out["매칭_대책수"] = 0
        out["포워딩_대책수"] = 0
        out["연결_대책목록"] = None
        out["등록여부"] = False
        return out

    lk = link.copy()
    lk["NUM"] = lk["NUM"].astype(str)
    out["NUM"] = out["NUM"].astype(str)

    def _agg(sub: pd.DataFrame, name: str) -> pd.Series:
        return sub.groupby("NUM")["CTE_SEQ"].nunique().rename(name)

    match = _agg(lk[lk["관계구분"] == schema.REL_MATCH], "매칭_대책수")
    fwd = _agg(lk[lk["관계구분"] == schema.REL_FORWARD], "포워딩_대책수")
    allcte = (lk.groupby("NUM")["CTE_SEQ"]
                .apply(lambda s: ", ".join(sorted(set(s.astype(str)))))
                .rename("연결_대책목록"))

    out = (out.merge(match, on="NUM", how="left")
              .merge(fwd, on="NUM", how="left")
              .merge(allcte, on="NUM", how="left"))
    out["매칭_대책수"] = out["매칭_대책수"].fillna(0).astype(int)
    out["포워딩_대책수"] = out["포워딩_대책수"].fillna(0).astype(int)
    # '등록'은 대책 본체 매칭 기준. 포워딩만 있는 건 등록으로 보지 않는다.
    out["등록여부"] = out["매칭_대책수"] > 0
    return out


def registration_by_ministry(epic: pd.DataFrame,
                             only_target: bool = True) -> pd.DataFrame:
    """부처별 EPTS 등록 현황 집계.

    only_target=True면 TOPIC에 P가 있는 '등록 대상' 자료만 센다.
    """
    df = epic
    if only_target and "등록대상" in df.columns:
        df = df[df["등록대상"]]
    if df.empty:
        return pd.DataFrame(columns=["부처", "대상", "등록", "미등록", "등록률"])

    g = (df.groupby("부처", dropna=False)
           .agg(대상=("NUM", "nunique"),
                등록=("등록여부", "sum"))
           .reset_index())
    g["등록"] = g["등록"].astype(int)
    g["미등록"] = g["대상"] - g["등록"]
    g["등록률"] = (g["등록"] / g["대상"] * 100).round(1)
    return g.sort_values(["미등록", "대상"], ascending=False, ignore_index=True)


def epts_links(cte_seq, link: pd.DataFrame, epic: pd.DataFrame) -> pd.DataFrame:
    """특정 대책에 연결된 EPIC 자료 목록 (매칭 + 포워딩)."""
    if link is None or link.empty:
        return pd.DataFrame()
    lk = link[link["CTE_SEQ"].astype(str) == str(cte_seq)].copy()
    if lk.empty:
        return lk
    lk["NUM"] = lk["NUM"].astype(str)
    cols = [c for c in ["NUM", "TITLE", "PUBLISHER1", "부처", "PUBLISH_DATE", "URL"]
            if c in epic.columns]
    e = epic.copy()
    e["NUM"] = e["NUM"].astype(str)
    merged = lk.merge(e[cols], on="NUM", how="left")

    # link는 전체 기간을 담지만 epic은 정부 기간으로 잘려 있다.
    # 기간 밖 자료는 제목이 비는데, URL은 NUM만으로 만들 수 있으니 살려 둔다.
    if "TITLE" in merged.columns:
        outside = merged["TITLE"].isna()
        if outside.any():
            merged.loc[outside, "TITLE"] = "(추출 기간 밖 자료)"
            if "URL" in merged.columns:
                merged.loc[outside, "URL"] = (
                    EIEC_VIEW_URL + merged.loc[outside, "NUM"].astype(str))

    keep = ["관계구분", "NUM", "TITLE", "부처", "PUBLISH_DATE",
            "추진내역명", "대표노출여부", "URL"]
    return merged[[c for c in keep if c in merged.columns]].sort_values(
        ["관계구분", "PUBLISH_DATE"], ascending=[True, False], ignore_index=True)


def linked_nums(cte_seq, link: pd.DataFrame) -> set[str]:
    """이미 해당 대책에 연결된 NUM 집합 — 추천에서 제외용."""
    if link is None or link.empty:
        return set()
    sub = link[link["CTE_SEQ"].astype(str) == str(cte_seq)]
    return set(sub["NUM"].astype(str))


def collect_sml(row: pd.Series, cols: list[str]) -> set[str]:
    """여러 소분류 컬럼의 값을 하나의 집합으로 (쉼표 연결값도 분해)."""
    out: set[str] = set()
    for c in cols:
        v = row.get(c)
        if isinstance(v, str) and v.strip():
            out |= {x.strip() for x in v.split(",") if x.strip()}
    return out
