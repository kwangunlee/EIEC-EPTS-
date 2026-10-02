"""기능 3 추천 엔진 — 대책(EPTS) 기준으로 붙을 만한 EPIC 자료를 찾는다.

하이브리드 점수
  1순위 (강) 주제코드 일치 : EPIC 매핑대상_소분류 ∩ 대책 테마_소분류
                             코드 기반이라 오탐이 적다. 앵커 역할.
  2순위 (중) 대/중분류 일치
  3순위 (보조) 키워드 유사도 : 제목·초록 ↔ 대책명·배경·내용

한국어는 형태소 분석기 없이도 문자 n-gram으로 충분히 동작해서
TfidfVectorizer(analyzer="char_wb")를 쓴다. 외부 API·사전이 필요 없다.

가중치는 WEIGHTS로 조정한다.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import schema, transform

WEIGHTS = {
    "소분류": 3.0,   # 코드 일치 — 가장 신뢰도 높음
    "중분류": 1.5,
    "대분류": 0.7,
    "키워드": 2.0,   # 코사인 유사도(0~1)에 곱해지는 계수
}


@dataclass
class RecoConfig:
    top_n: int = 20
    only_topic_p: bool = True      # 등록 대상(TOPIC=P) 자료만 후보로
    exclude_linked: bool = True    # 이미 연결된 자료는 제외
    min_score: float = 0.3


def _text_of_epts(row: pd.Series) -> str:
    parts = [row.get("CTE_NM"), row.get("정책배경"), row.get("정책내용"),
             row.get("대책설명")]
    return " ".join(str(p) for p in parts if isinstance(p, str) and p.strip())


def _text_of_epic(df: pd.DataFrame) -> pd.Series:
    cols = [c for c in ("TITLE", "ABSTRACT") if c in df.columns]
    if not cols:
        return pd.Series([""] * len(df), index=df.index)
    return (df[cols].fillna("").astype(str)
            .agg(" ".join, axis=1).str.strip())


def keyword_scores(query: str, docs: pd.Series) -> pd.Series:
    """문자 n-gram TF-IDF 코사인 유사도 (0~1). scikit-learn 없으면 0."""
    if not query.strip() or docs.empty:
        return pd.Series(0.0, index=docs.index)
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        return pd.Series(0.0, index=docs.index)

    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 3),
                          min_df=1, sublinear_tf=True)
    try:
        matrix = vec.fit_transform(pd.concat([pd.Series([query]), docs]))
    except ValueError:        # 어휘가 비는 경우
        return pd.Series(0.0, index=docs.index)
    sims = cosine_similarity(matrix[0:1], matrix[1:]).ravel()
    return pd.Series(sims, index=docs.index)


def recommend(cte_row: pd.Series, epic: pd.DataFrame, link: pd.DataFrame,
              cfg: RecoConfig | None = None) -> pd.DataFrame:
    """대책 1건에 대해 연결 후보 EPIC을 점수순으로 돌려준다."""
    cfg = cfg or RecoConfig()
    if epic.empty:
        return pd.DataFrame()

    cand = epic
    if cfg.only_topic_p and "등록대상" in cand.columns:
        cand = cand[cand["등록대상"]]
    if cfg.exclude_linked:
        done = transform.linked_nums(cte_row.get("CTE_SEQ"), link)
        cand = cand[~cand["NUM"].astype(str).isin(done)]
    if cand.empty:
        return pd.DataFrame()

    cand = cand.copy()

    # ── 1·2순위: 주제코드(테마명) 일치 ──────────────────────────
    t_sml = transform.collect_sml(cte_row, ["테마_소분류1", "테마_소분류2", "테마_소분류3"])
    t_mid = transform.collect_sml(cte_row, ["테마_중분류1", "테마_중분류2", "테마_중분류3"])
    t_big = transform.collect_sml(cte_row, ["테마_대분류1", "테마_대분류2", "테마_대분류3"])

    e_sml = [schema.subject_cols(i)["sml"] for i in schema.SUBJECT_SLOTS]
    e_mid = [schema.subject_cols(i)["mid"] for i in schema.SUBJECT_SLOTS]
    e_big = [schema.subject_cols(i)["big"] for i in schema.SUBJECT_SLOTS]

    def _overlap(row, cols, target):
        if not target:
            return ""
        hit = transform.collect_sml(row, cols) & target
        return ", ".join(sorted(hit))

    cand["일치_소분류"] = cand.apply(lambda r: _overlap(r, e_sml, t_sml), axis=1)
    cand["일치_중분류"] = cand.apply(lambda r: _overlap(r, e_mid, t_mid), axis=1)
    cand["일치_대분류"] = cand.apply(lambda r: _overlap(r, e_big, t_big), axis=1)

    # ── 3순위: 키워드 유사도 ────────────────────────────────────
    cand["유사도"] = keyword_scores(_text_of_epts(cte_row),
                                   _text_of_epic(cand)).round(3)

    # ── 합산 ────────────────────────────────────────────────────
    cand["점수"] = (
        cand["일치_소분류"].ne("").astype(float) * WEIGHTS["소분류"]
        + cand["일치_중분류"].ne("").astype(float) * WEIGHTS["중분류"]
        + cand["일치_대분류"].ne("").astype(float) * WEIGHTS["대분류"]
        + cand["유사도"] * WEIGHTS["키워드"]
    ).round(3)

    cand["근거"] = cand.apply(_reason, axis=1)

    out = cand[cand["점수"] >= cfg.min_score].sort_values(
        "점수", ascending=False, ignore_index=True).head(cfg.top_n)

    cols = [c for c in ["점수", "근거", "NUM", "TITLE", "부처", "PUBLISH_DATE",
                        "일치_소분류", "유사도", "URL"] if c in out.columns]
    return out[cols]


def _reason(row: pd.Series) -> str:
    bits = []
    if row.get("일치_소분류"):
        bits.append(f"소분류 일치({row['일치_소분류']})")
    elif row.get("일치_중분류"):
        bits.append(f"중분류 일치({row['일치_중분류']})")
    elif row.get("일치_대분류"):
        bits.append(f"대분류 일치({row['일치_대분류']})")
    if row.get("유사도", 0) >= 0.1:
        bits.append(f"키워드 유사 {row['유사도']:.2f}")
    return " · ".join(bits) if bits else "약한 신호"
