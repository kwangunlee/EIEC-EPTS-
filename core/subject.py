"""주제 체계 분석 — EIEC 주제 ↔ EPTS 테마

원칙: **매칭·집계는 코드로, 표시는 한글명으로.**
코드는 안정적이지만 사람이 못 읽고, 이름은 읽히지만 중복·변경된다.
그래서 모든 함수는 코드로 계산한 뒤 마스터에서 이름을 끌어와 붙인다.

두 체계는 서로 독립이다.
  EIEC/EPIC : J_CODE 5자리 (예 C0501). 계층은 자리수로 추정 — 마스터에 부모 컬럼 없음
  EPTS      : RELT_THEM_CD + HRNK_RELT_THEM_CD 자기참조 트리
둘을 잇는 것은 EIEC.EPTS_RELATION 하나뿐이고, 그 결과가 subject_map이다.
"""
from __future__ import annotations

import pandas as pd

from . import schema


# ── 공통 ────────────────────────────────────────────────────────
def _codes_long(df: pd.DataFrame, code_cols: list[str],
                key: str, code_name: str = "코드") -> pd.DataFrame:
    """여러 코드 슬롯을 세로로 편다. 빈 값·미지정 코드는 버린다."""
    cols = [c for c in code_cols if c in df.columns]
    if not cols or df.empty:
        return pd.DataFrame(columns=[key, code_name])
    long = df.melt(id_vars=[key], value_vars=cols,
                   var_name="슬롯", value_name=code_name)
    long[code_name] = long[code_name].astype("string").str.strip()
    long = long[long[code_name].notna()
                & (long[code_name] != "")
                & (long[code_name] != schema.NULL_SUBJECT_CODE)]
    return long.drop_duplicates([key, code_name])


def name_lookup(master: pd.DataFrame, code_col: str,
                name_col: str) -> pd.Series:
    """코드 → 한글명 매핑 Series. 표시 단계에서만 쓴다."""
    if master.empty or code_col not in master.columns:
        return pd.Series(dtype="object")
    m = master.dropna(subset=[code_col]).drop_duplicates(code_col)
    return pd.Series(m[name_col].values,
                     index=m[code_col].astype(str).str.strip())


# ── EIEC 주제 ───────────────────────────────────────────────────
def epic_subject_usage(epic: pd.DataFrame,
                       subject_eiec: pd.DataFrame) -> pd.DataFrame:
    """주제코드별 EPIC 자료 건수. 자료가 0건인 주제도 남긴다."""
    if subject_eiec.empty:
        return pd.DataFrame()

    base = subject_eiec.copy()
    base["주제코드"] = base["주제코드"].astype(str).str.strip()

    if epic.empty:
        base["자료수"] = 0
        base["등록대상수"] = 0
        return base

    long = _codes_long(epic, schema.EPIC_SUBJECT_CODE_COLS, "NUM", "주제코드")
    cnt = long.groupby("주제코드").size().rename("자료수")

    # 등록 대상(TOPIC=P)만 따로
    if "등록대상" in epic.columns:
        tgt = epic.loc[epic["등록대상"], ["NUM"]]
        long_t = long[long["NUM"].isin(tgt["NUM"])]
        cnt_t = long_t.groupby("주제코드").size().rename("등록대상수")
    else:
        cnt_t = pd.Series(dtype=int, name="등록대상수")

    out = base.merge(cnt, left_on="주제코드", right_index=True, how="left") \
              .merge(cnt_t, left_on="주제코드", right_index=True, how="left")
    out["자료수"] = out["자료수"].fillna(0).astype(int)
    out["등록대상수"] = out["등록대상수"].fillna(0).astype(int)
    return out


def orphan_subject_codes(epic: pd.DataFrame,
                         subject_eiec: pd.DataFrame) -> pd.DataFrame:
    """자료에는 쓰였는데 주제 마스터에 없는 코드 — 데이터 정합성 점검."""
    if epic.empty or subject_eiec.empty:
        return pd.DataFrame(columns=["주제코드", "자료수"])
    known = set(subject_eiec["주제코드"].astype(str).str.strip())
    long = _codes_long(epic, schema.EPIC_SUBJECT_CODE_COLS, "NUM", "주제코드")
    bad = long[~long["주제코드"].isin(known)]
    if bad.empty:
        return pd.DataFrame(columns=["주제코드", "자료수"])
    return (bad.groupby("주제코드").size().rename("자료수")
               .reset_index().sort_values("자료수", ascending=False,
                                          ignore_index=True))


# ── EPTS 테마 ───────────────────────────────────────────────────
def epts_theme_usage(epts: pd.DataFrame,
                     subject_epts: pd.DataFrame) -> pd.DataFrame:
    """테마코드별 대책 건수. 소분류 기준으로 센다."""
    if subject_epts.empty:
        return pd.DataFrame()

    base = subject_epts.copy()
    base["테마코드"] = base["테마코드"].astype(str).str.strip()

    if epts.empty:
        base["대책수"] = 0
        return base

    long = _codes_long(epts, schema.EPTS_THEME_CODE_COLS, "CTE_SEQ", "테마코드")
    cnt = long.groupby("테마코드").size().rename("대책수")
    out = base.merge(cnt, left_on="테마코드", right_index=True, how="left")
    out["대책수"] = out["대책수"].fillna(0).astype(int)
    return out


# ── 매핑 현황 ───────────────────────────────────────────────────
def mapping_coverage(subject_eiec: pd.DataFrame, subject_map: pd.DataFrame,
                     epic: pd.DataFrame | None = None) -> dict:
    """EIEC 주제가 EPTS 테마로 얼마나 매핑돼 있는지 요약."""
    if subject_eiec.empty:
        return {}
    codes = set(subject_eiec["주제코드"].astype(str).str.strip())
    codes.discard(schema.NULL_SUBJECT_CODE)
    mapped = (set(subject_map["주제코드"].astype(str).str.strip())
              if not subject_map.empty else set())
    hit = codes & mapped

    out = {"전체 주제": len(codes), "매핑됨": len(hit),
           "미매핑": len(codes - hit),
           "매핑률": round(len(hit) / len(codes) * 100, 1) if codes else 0.0}

    # 미매핑 주제에 실제 자료가 얼마나 걸려 있는지 — 영향도
    if epic is not None and not epic.empty:
        long = _codes_long(epic, schema.EPIC_SUBJECT_CODE_COLS, "NUM", "주제코드")
        out["미매핑 주제의 자료"] = int(
            long[long["주제코드"].isin(codes - hit)]["NUM"].nunique())
    return out


def unmapped_subjects(subject_eiec: pd.DataFrame, subject_map: pd.DataFrame,
                      usage: pd.DataFrame | None = None) -> pd.DataFrame:
    """EPTS 테마에 매핑되지 않은 EIEC 주제 목록 (자료 많은 순)."""
    if subject_eiec.empty:
        return pd.DataFrame()
    mapped = (set(subject_map["주제코드"].astype(str).str.strip())
              if not subject_map.empty else set())
    src = usage if usage is not None and not usage.empty else subject_eiec
    out = src.copy()
    out["주제코드"] = out["주제코드"].astype(str).str.strip()
    out = out[(~out["주제코드"].isin(mapped))
              & (out["주제코드"] != schema.NULL_SUBJECT_CODE)]
    cols = [c for c in ["주제코드", "주제명", "대분류코드", "중분류코드",
                        "중분류명", "자료수", "등록대상수"] if c in out.columns]
    out = out[cols]
    if "자료수" in out.columns:
        out = out.sort_values("자료수", ascending=False, ignore_index=True)
    return out


def unused_themes(subject_epts: pd.DataFrame,
                  subject_map: pd.DataFrame) -> pd.DataFrame:
    """어떤 EIEC 주제도 가리키지 않는 EPTS 테마 (소분류 기준)."""
    if subject_epts.empty:
        return pd.DataFrame()
    mapped = (set(subject_map["테마코드"].astype(str).str.strip())
              if not subject_map.empty else set())
    out = subject_epts.copy()
    out["테마코드"] = out["테마코드"].astype(str).str.strip()
    if "깊이" in out.columns:
        out = out[pd.to_numeric(out["깊이"], errors="coerce") >= 3]
    out = out[~out["테마코드"].isin(mapped)]
    cols = [c for c in ["테마코드", "테마명", "대분류명", "중분류명",
                        "대책수", "사용여부"] if c in out.columns]
    return out[cols].reset_index(drop=True)


def mapping_pairs(subject_map: pd.DataFrame,
                  level: str = "소분류") -> pd.DataFrame:
    """매핑 쌍 목록. 코드로 걸러 이름과 함께 보여준다."""
    if subject_map.empty:
        return pd.DataFrame()
    out = subject_map
    if level and "매핑단계" in out.columns:
        out = out[out["매핑단계"] == level]
    cols = [c for c in ["주제코드", "주제명", "매핑단계", "테마코드", "테마명",
                        "주제코드_미존재", "테마코드_미존재"] if c in out.columns]
    return out[cols].reset_index(drop=True)


def broken_mappings(subject_map: pd.DataFrame) -> pd.DataFrame:
    """양쪽 마스터에 없는 코드를 가리키는 매핑 — 깨진 연결."""
    if subject_map.empty:
        return pd.DataFrame()
    mask = pd.Series(False, index=subject_map.index)
    for col in ("주제코드_미존재", "테마코드_미존재"):
        if col in subject_map.columns:
            mask |= subject_map[col].astype(str).str.upper().eq("Y")
    return subject_map[mask].reset_index(drop=True)
