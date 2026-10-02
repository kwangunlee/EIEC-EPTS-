"""HTML 원문 정제 — 노트북(clean_epic.ipynb)의 로직을 그대로 옮긴 것.

정제 순서가 중요하다
  1) html.unescape() 2회  — 이중 인코딩 대응 (&amp;lt; → &lt; → <)
                            HTML5 표준 엔티티 2,200여 개를 한 번에 처리
  2) 블록 태그 → 줄바꿈   — <p> </li> <br> (구조 보존)
  3) 나머지 태그 제거     — 반드시 디코딩 이후. 순서를 바꾸면 &lt;p&gt;를 못 잡는다
  4) 공백·제어문자 정리

<추진목표>처럼 꺾쇠로 감싼 한글 표기는 태그가 아니므로 보존한다.
"""
from __future__ import annotations

import html
import re

import pandas as pd

from . import schema

LI = re.compile(r"<\s*li\b[^>]*>", re.I)
BLOCK = re.compile(
    r"<\s*/?\s*(p|div|br|tr|h[1-6]|ul|ol|li|table|blockquote)\b[^>]*>", re.I)
# 실제 HTML 태그만 제거. <추진목표> 같은 한글 표기는 본문이므로 보존
TAG = re.compile(r"</?[a-zA-Z][a-zA-Z0-9]*(?:\s[^<>]*)?/?>")
CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
NBSP = re.compile(r"[ ​﻿]")
SPACES = re.compile(r"[ \t]+")
NEWLINE = re.compile(r"\s*\n\s*")
MULTINL = re.compile(r"\n{2,}")
# 정제 후에도 엔티티·태그가 남았는지 검사하는 패턴
DIRTY = re.compile(
    r"&[a-zA-Z#][a-zA-Z0-9]{1,9};|</?[a-zA-Z][a-zA-Z0-9]*(?:\s[^<>]*)?/?>")


def is_text(sr: pd.Series) -> bool:
    """pandas 2.x(object) / 3.x(StringDtype) 양쪽에서 문자열 컬럼 판정"""
    return pd.api.types.is_string_dtype(sr) or sr.dtype == object


def clean(s, maxlen: int | None = None, flat: bool = False):
    """HTML 원문 → 읽을 수 있는 평문. 빈 값은 None."""
    if not isinstance(s, str) or not s:
        return None if s == "" else s

    s = html.unescape(html.unescape(s))
    s = LI.sub("\n• ", s)
    s = BLOCK.sub("\n", s)
    s = TAG.sub(" ", s)
    s = NBSP.sub(" ", s)
    s = CTRL.sub("", s)
    s = SPACES.sub(" ", s)
    s = NEWLINE.sub("\n", s)
    s = MULTINL.sub("\n", s)
    s = s.strip(" \n•")

    if flat:
        s = SPACES.sub(" ", s.replace("\n", " ")).strip()
    if not s:
        return None
    if maxlen and len(s) > maxlen:
        s = s[:maxlen].rstrip() + "…"
    return s


def clean_frame(df: pd.DataFrame, maxlen: int | None = None,
                skip: set[str] | None = None) -> pd.DataFrame:
    """데이터프레임의 모든 텍스트 컬럼을 정제한다 (식별자·날짜 제외)."""
    skip = schema.SKIP_CLEAN if skip is None else skip
    out = df.copy()
    for col in out.columns:
        if col in skip or not is_text(out[col]):
            continue
        out[col] = out[col].map(lambda v: clean(v, maxlen))
    return out


def dirty_report(df: pd.DataFrame, skip: set[str] | None = None) -> pd.DataFrame:
    """컬럼별 잔여 오염(엔티티·태그) 건수. 0이면 깨끗한 것."""
    skip = schema.SKIP_CLEAN if skip is None else skip
    rows = []
    for col in df.columns:
        if col in skip or not is_text(df[col]):
            continue
        s = df[col].dropna().astype(str)
        n = int(s.str.contains(DIRTY, regex=True, na=False).sum()) if len(s) else 0
        if n:
            sample = s[s.str.contains(DIRTY, regex=True, na=False)].iloc[0][:120]
            rows.append({"컬럼": col, "잔여": n, "예시": sample})
    return pd.DataFrame(rows, columns=["컬럼", "잔여", "예시"])
