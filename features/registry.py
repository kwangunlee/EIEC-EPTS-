"""기능 등록부 — 새 기능은 여기 한 줄만 추가한다."""
from __future__ import annotations

from .base import Page
from . import (f1_registration, f2_epts_detail, f3_recommend,
               f4_subject, f9_admin)

PAGES: list[Page] = [
    f1_registration.PAGE,
    f2_epts_detail.PAGE,
    f3_recommend.PAGE,
    f4_subject.PAGE,
    f9_admin.PAGE,
    # 새 기능: from . import f5_xxx  →  f5_xxx.PAGE 를 여기 추가
]

BY_KEY = {p.key: p for p in PAGES}
