"""페이지 공통 인터페이스 + 재사용 위젯."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd
import streamlit as st

from core.loader import Bundle

# ── 폭 지정 인자 (Streamlit 버전 차이 흡수) ─────────────────────
# 신버전: width="stretch" / 구버전: use_container_width=True
try:
    import inspect as _inspect
    _WIDE = ({"width": "stretch"}
             if "width" in _inspect.signature(st.dataframe).parameters
             else {"use_container_width": True})
except (TypeError, ValueError):
    _WIDE = {"use_container_width": True}

WIDE = _WIDE


@dataclass(frozen=True)
class Page:
    """기능 하나를 나타낸다. render(bundle)만 구현하면 된다."""
    key: str
    label: str
    icon: str
    render: Callable[[Bundle], None]
    help: str = ""


def need(bundle: Bundle, *datasets: str) -> bool:
    """필요한 데이터셋이 비어 있으면 안내하고 False."""
    missing = [d for d in datasets if getattr(bundle, d, pd.DataFrame()).empty]
    if missing:
        st.warning(
            f"이 기능은 **{', '.join(missing)}** 데이터가 필요합니다. "
            "사이드바의 *데이터 갱신*에서 올리거나, `data/` 폴더에 넣어 주세요."
        )
        return False
    return True


def download_button(df: pd.DataFrame, filename: str, label: str = "CSV 내려받기"):
    st.download_button(
        label,
        df.to_csv(index=False).encode("utf-8-sig"),
        file_name=filename,
        mime="text/csv",
        **WIDE,
    )


def metric_row(items: list[tuple[str, object]]):
    for col, (label, value) in zip(st.columns(len(items)), items):
        col.metric(label, value)


def link_column_config(df: pd.DataFrame) -> dict:
    """URL 컬럼을 클릭 가능한 링크로."""
    cfg = {}
    if "URL" in df.columns:
        cfg["URL"] = st.column_config.LinkColumn("링크", display_text="열기", width="small")
    if "TITLE" in df.columns:
        cfg["TITLE"] = st.column_config.TextColumn("제목", width="large")
    return cfg
