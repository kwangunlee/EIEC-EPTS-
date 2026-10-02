"""KDI 정책정보허브 — EPIC ↔ EPTS 작업 지원 도구

이 파일은 라우팅만 한다. 기능은 features/ 아래 모듈에 있고,
features/registry.py 의 PAGES 목록으로 등록된다.
"""
from __future__ import annotations

import streamlit as st

from core import loader
from features import registry
from features.base import WIDE

st.set_page_config(page_title="정책정보허브", page_icon="📊", layout="wide")


@st.cache_data(show_spinner="데이터 읽는 중…")
def _bundle():
    return loader.load_bundle()


def main() -> None:
    bundle = _bundle()

    with st.sidebar:
        st.markdown("### 정책정보허브")
        st.caption("EPIC ↔ EPTS 작업 지원")

        st.markdown(f"**기준 시점**  \n{bundle.updated_at}")
        if bundle.manifest.get("비고"):
            st.caption(bundle.manifest["비고"])
        c = bundle.counts()
        st.caption(f"자료 {c['epic']:,} · 대책 {c['epts']:,} · 연결 {c['link']:,}")

        if st.button("데이터 다시 읽기", **WIDE):
            _bundle.clear()
            st.rerun()

        st.divider()
        choice = st.radio(
            "기능",
            [p.key for p in registry.PAGES],
            format_func=lambda k: f"{registry.BY_KEY[k].icon} {registry.BY_KEY[k].label}",
            label_visibility="collapsed",
        )
        page = registry.BY_KEY[choice]
        if page.help:
            st.caption(page.help)

        problems = loader.validate(bundle)
        if problems:
            st.divider()
            with st.expander("데이터 점검", expanded=False):
                for p in problems:
                    st.warning(p)

    page.render(bundle)


if __name__ == "__main__":
    main()
