"""데이터 갱신 (관리자용)

쿼리 결과 CSV를 올리면 → HTML 정제 → 검증 → `data/` 에 넣을 묶음을 만든다.
Streamlit Cloud의 파일시스템은 휘발성이라 repo에 직접 쓰지 않는다.
만들어진 파일을 내려받아 GitHub에 커밋하는 방식이다.
"""
from __future__ import annotations

import io
import zipfile

import pandas as pd
import streamlit as st

from core import clean, loader, schema
from .base import Page, WIDE

UPLOADS = [
    (schema.EPIC, "01_epic.sql 결과", "자료 1건 = 1행"),
    (schema.EPTS, "02_epts.sql 결과", "대책 1건 = 1행"),
    (schema.LINK, "03_link.sql 결과", "NUM × CTE_SEQ 관계"),
    (schema.SUBJ_EIEC, "04_subject_eiec.sql 결과", "EIEC 주제 체계"),
    (schema.SUBJ_EPTS, "05_subject_epts.sql 결과", "EPTS 테마 체계"),
    (schema.SUBJ_MAP, "06_subject_map.sql 결과", "주제 ↔ 테마 매핑"),
]


def _read(upload) -> pd.DataFrame:
    raw = upload.getvalue()
    for enc in ("utf-8-sig", "cp949"):
        try:
            return pd.read_csv(io.BytesIO(raw), dtype=str, encoding=enc,
                               keep_default_na=False, na_values=schema.NA_STRINGS)
        except UnicodeDecodeError:
            continue
    raise ValueError("인코딩을 알 수 없습니다 (utf-8 / cp949 모두 실패)")


def render(bundle: loader.Bundle) -> None:
    st.subheader("데이터 갱신")
    st.caption("쿼리 결과를 올리면 정제·검증한 뒤 `data/` 에 커밋할 파일을 만들어 줍니다. "
               "팀원은 커밋된 스냅샷을 보게 됩니다.")

    with st.expander("현재 스냅샷", expanded=True):
        m = bundle.manifest
        if m:
            st.write(f"**기준 시점** {m.get('생성일시', '미상')}"
                     f" · 작성 {m.get('작성자', '-')}")
            st.json(m.get("건수", {}), expanded=False)
        else:
            st.info("아직 스냅샷이 없습니다.")

    st.markdown("##### 1. 파일 올리기")
    files, frames = {}, {}
    for key, title, hint in UPLOADS:
        up = st.file_uploader(f"{title} — {hint}", type=["csv"], key=f"up_{key}")
        if up is not None:
            files[key] = up

    if not files:
        st.caption("주제 체계(04~06)는 자주 바뀌지 않으므로 01~03만 갱신해도 됩니다.")
        return

    maxlen = st.number_input("본문 최대 길이 (0 = 제한 없음)", 0, 20000, 1000, step=100)

    st.markdown("##### 2. 정제 · 검증")
    problems = []
    for key, up in files.items():
        try:
            df = _read(up)
        except ValueError as e:
            st.error(f"{key}: {e}")
            continue

        cleaned = clean.clean_frame(df, maxlen=int(maxlen) or None)
        frames[key] = cleaned

        missing = [c for c in schema.REQUIRED[key] if c not in cleaned.columns]
        dirty = clean.dirty_report(cleaned)

        with st.container(border=True):
            st.markdown(f"**{key}** — {len(cleaned):,}행 × {len(cleaned.columns)}열")
            if missing:
                problems.append(f"{key}: 필수 컬럼 누락 {missing}")
                st.error(f"필수 컬럼 누락: {missing}")
            if not dirty.empty:
                problems.append(f"{key}: HTML 잔여 {int(dirty['잔여'].sum())}건")
                st.warning("정제되지 않은 HTML이 남아 있습니다.")
                st.dataframe(dirty, hide_index=True, **WIDE)
            if not missing and dirty.empty:
                st.success("구조·정제 모두 정상")
            st.dataframe(cleaned.head(3), **WIDE)

    if problems:
        st.error("문제를 해결한 뒤 내려받으세요: " + " / ".join(problems))

    st.markdown("##### 3. 내려받아 커밋")
    author = st.text_input("작성자", value="")
    note = st.text_input("비고", placeholder="예: 2026년 상반기분 반영")

    manifest = {
        "생성일시": loader.now_kst(),
        "작성자": author or "-",
        "비고": note,
        "건수": {k: len(v) for k, v in frames.items()},
        "컬럼": {k: list(v.columns) for k, v in frames.items()},
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for key, df in frames.items():
            z.writestr(f"data/{key}.csv", df.to_csv(index=False, encoding="utf-8-sig"))
        z.writestr("data/manifest.json",
                   pd.Series(manifest).to_json(force_ascii=False, indent=2))

    st.download_button(
        "data 묶음 내려받기 (zip)", buf.getvalue(),
        file_name=f"data_{loader.now_kst().replace(' ', '_').replace(':', '')}.zip",
        mime="application/zip", **WIDE,
        disabled=bool(problems) or not frames,
    )
    st.caption("압축을 풀어 저장소의 `data/` 에 덮어쓰고 커밋·푸시하면 팀원 화면이 갱신됩니다.")


PAGE = Page(
    key="f9",
    label="데이터 갱신",
    icon="⚙️",
    render=render,
    help="쿼리 결과를 정제해 커밋용 파일 생성 (관리자)",
)
