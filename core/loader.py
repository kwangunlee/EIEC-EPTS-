"""데이터 적재 — data/ 폴더의 스냅샷을 읽어 캐시한다.

팀원은 관리자가 올려둔 스냅샷을 그대로 본다.
manifest.json이 '언제 기준 데이터인지'를 알려준다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd

from . import schema

KST = timezone(timedelta(hours=9))
_EMPTY = pd.DataFrame()
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MANIFEST = DATA_DIR / "manifest.json"


@dataclass
class Bundle:
    """앱 전체가 공유하는 데이터 묶음."""
    epic: pd.DataFrame = field(default_factory=pd.DataFrame)
    epts: pd.DataFrame = field(default_factory=pd.DataFrame)
    link: pd.DataFrame = field(default_factory=pd.DataFrame)
    subject_eiec: pd.DataFrame = field(default_factory=pd.DataFrame)
    subject_epts: pd.DataFrame = field(default_factory=pd.DataFrame)
    subject_map: pd.DataFrame = field(default_factory=pd.DataFrame)
    manifest: dict = field(default_factory=dict)

    @property
    def updated_at(self) -> str:
        return self.manifest.get("생성일시", "미상")

    @property
    def is_empty(self) -> bool:
        return self.epic.empty and self.epts.empty

    def frame(self, name: str) -> pd.DataFrame:
        """데이터셋 이름으로 꺼낸다. 없는 이름이면 빈 프레임.

        schema와 loader의 버전이 어긋나도(배포 시 일부 파일만 갱신되는 경우)
        죽지 않고 validate()가 문제를 보고하게 한다.
        """
        return getattr(self, name, _EMPTY)

    def missing_fields(self) -> list[str]:
        """schema.DATASETS에 있는데 Bundle에 필드가 없는 것 — 버전 불일치 신호"""
        return [n for n in schema.DATASETS if not hasattr(self, n)]

    def counts(self) -> dict[str, int]:
        return {name: len(self.frame(name)) for name in schema.DATASETS}


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
    # Bundle이 실제로 가진 필드만 채운다 (schema와 어긋나도 생성은 성공하도록)
    known = {f.name for f in fields(Bundle)}
    frames = {name: _read_one(name, d)
              for name in schema.DATASETS if name in known}

    epic, link = frames[schema.EPIC], frames[schema.LINK]
    if not epic.empty:
        epic = transform.enrich_epic(epic)
        epic = transform.attach_link_status(epic, link)
        frames[schema.EPIC] = epic

    return Bundle(**frames, manifest=read_manifest(d))


def validate(bundle: Bundle) -> list[str]:
    """필수 컬럼 누락 등 구조 문제를 문자열 목록으로 돌려준다."""
    problems: list[str] = []

    gone = bundle.missing_fields()
    if gone:
        problems.append(
            f"⚠ 코드 버전 불일치 — loader.py에 {gone} 필드가 없습니다. "
            "저장소의 core/ 파일을 모두 최신으로 올렸는지 확인하세요.")

    for name in schema.DATASETS:
        df = bundle.frame(name)
        if df.empty:
            problems.append(f"{name}: 데이터 없음")
            continue
        missing = [c for c in schema.REQUIRED[name] if c not in df.columns]
        if missing:
            problems.append(f"{name}: 필수 컬럼 누락 {missing}")
    return problems
