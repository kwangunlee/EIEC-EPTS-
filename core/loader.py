"""데이터 적재 — data/ 폴더의 스냅샷을 읽어 캐시한다.

팀원은 관리자가 올려둔 스냅샷을 그대로 본다.
manifest.json이 '언제 기준 데이터인지'를 알려준다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd

from . import schema

KST = timezone(timedelta(hours=9))
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MANIFEST = DATA_DIR / "manifest.json"


@dataclass
class Bundle:
    """앱 전체가 공유하는 데이터 묶음."""
    epic: pd.DataFrame = field(default_factory=pd.DataFrame)
    epts: pd.DataFrame = field(default_factory=pd.DataFrame)
    link: pd.DataFrame = field(default_factory=pd.DataFrame)
    manifest: dict = field(default_factory=dict)

    @property
    def updated_at(self) -> str:
        return self.manifest.get("생성일시", "미상")

    @property
    def is_empty(self) -> bool:
        return self.epic.empty and self.epts.empty

    def counts(self) -> dict[str, int]:
        return {schema.EPIC: len(self.epic),
                schema.EPTS: len(self.epts),
                schema.LINK: len(self.link)}


def _read_one(name: str, data_dir: Path) -> pd.DataFrame:
    """parquet 우선, 없으면 csv. 둘 다 없으면 빈 프레임."""
    pq = data_dir / f"{name}.parquet"
    if pq.exists():
        return pd.read_parquet(pq)
    csv = data_dir / f"{name}.csv"
    if csv.exists():
        return pd.read_csv(csv, dtype=str, keep_default_na=False,
                           na_values=schema.NA_STRINGS, encoding="utf-8-sig")
    return pd.DataFrame()


def read_manifest(data_dir: Path | None = None) -> dict:
    d = Path(data_dir) if data_dir else DATA_DIR
    f = d / "manifest.json"
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def write_manifest(info: dict, data_dir: Path | None = None) -> Path:
    d = Path(data_dir) if data_dir else DATA_DIR
    d.mkdir(parents=True, exist_ok=True)
    f = d / "manifest.json"
    f.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    return f


def now_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M")


def load_bundle(data_dir: Path | None = None) -> Bundle:
    """data/ 에서 세 데이터셋을 읽어 파생 컬럼까지 붙인 Bundle 반환."""
    from . import transform  # 순환 import 방지

    d = Path(data_dir) if data_dir else DATA_DIR
    epic = _read_one(schema.EPIC, d)
    epts = _read_one(schema.EPTS, d)
    link = _read_one(schema.LINK, d)

    if not epic.empty:
        epic = transform.enrich_epic(epic)
        epic = transform.attach_link_status(epic, link)

    return Bundle(epic=epic, epts=epts, link=link, manifest=read_manifest(d))


def validate(bundle: Bundle) -> list[str]:
    """필수 컬럼 누락 등 구조 문제를 문자열 목록으로 돌려준다."""
    problems: list[str] = []
    for name, df in ((schema.EPIC, bundle.epic),
                     (schema.EPTS, bundle.epts),
                     (schema.LINK, bundle.link)):
        if df.empty:
            problems.append(f"{name}: 데이터 없음")
            continue
        missing = [c for c in schema.REQUIRED[name] if c not in df.columns]
        if missing:
            problems.append(f"{name}: 필수 컬럼 누락 {missing}")
    return problems
