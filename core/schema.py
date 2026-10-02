"""데이터 스키마 상수 — 컬럼명·타입·정의를 한 곳에서 관리한다.

컬럼이 늘거나 이름이 바뀌면 이 파일만 고친다.
"""
from __future__ import annotations

# ── 데이터셋 이름 ───────────────────────────────────────────────
EPIC = "epic"
EPTS = "epts"
LINK = "link"
DATASETS = (EPIC, EPTS, LINK)

# ── 키 ──────────────────────────────────────────────────────────
KEY_EPIC = "NUM"
KEY_EPTS = "CTE_SEQ"

# ── CSV 읽기 ────────────────────────────────────────────────────
# DBeaver가 NULL을 글자로 내보내는 경우가 있어 빈칸으로 환원한다
NA_STRINGS = ["", "null", "NULL", "[NULL]", "<null>", "(null)",
              "nan", "NaN", "None", "N/A", "n/a", "#N/A", "-"]

# HTML 정제에서 제외할 컬럼 (식별자·날짜·URL)
SKIP_CLEAN = {
    "NUM", "CTE_SEQ", "URL", "PUBLISH_DATE", "발표일자",
    "FRWD_HIST_SEQ", "순서", "등록일시", "수정일시",
    "추진내역_최종수정", "추진내역_건수", "매칭_EPIC수", "포워딩_EPIC수", "조회수",
}

# ── 각 데이터셋에서 반드시 있어야 하는 컬럼 ─────────────────────
REQUIRED = {
    EPIC: ["NUM", "PUBLISHER1", "TITLE", "PUBLISH_DATE"],
    EPTS: ["CTE_SEQ", "CTE_NM"],
    LINK: ["NUM", "CTE_SEQ", "관계구분"],
}

# ── 관계구분 값 ─────────────────────────────────────────────────
REL_MATCH = "매칭"
REL_FORWARD = "포워딩"

# ── EPIC 주제 슬롯 (1~3) ────────────────────────────────────────
SUBJECT_SLOTS = (1, 2, 3)


def subject_cols(slot: int) -> dict[str, str]:
    """주제 슬롯 n의 컬럼명 묶음"""
    return {
        "name": f"SUBJECT_NAME{slot}",
        "big": f"매핑대상_대분류{slot}",
        "mid": f"매핑대상_중분류{slot}",
        "sml": f"매핑대상_소분류{slot}",
    }


def epic_sml_cols() -> list[str]:
    """EPIC의 매핑대상 소분류 컬럼 전체 — 주제코드 기반 매칭의 앵커"""
    return [subject_cols(i)["sml"] for i in SUBJECT_SLOTS]


def epts_sml_cols() -> list[str]:
    """EPTS 대책의 테마 소분류 컬럼 전체"""
    return [f"테마_소분류{i}" for i in (1, 2, 3)]


# ── 컬럼 정의서 (컬럼명, 한글명, 원천, 타입, 설명, 근거) ────────
# 근거: 스키마주석 = 정의서 CSV 코멘트 / 조인정의 = 쿼리 파생 / 분석확인 = 실데이터 확인
COLUMN_DEFS: dict[str, list[tuple]] = {
    EPIC: [
        ("NUM", "자료 일련번호", "EPIC.ECO_POLICY_INFO.NUM", "NUMBER",
         "EPIC 정책자료 고유키", "스키마주석"),
        ("PUBLISHER1", "발간부서", "EPIC.ECO_POLICY_INFO.PUBLISHER1", "VARCHAR2(100)",
         "발간부서 전체 경로명. 첫 토큰이 부처", "분석확인"),
        ("TITLE", "제목", "EPIC.ECO_POLICY_INFO.TITLE", "VARCHAR2(500)",
         "자료 제목", "스키마주석"),
        ("ABSTRACT", "초록", "EPIC.ECO_POLICY_INFO.ABSTRACT", "VARCHAR2(2000)",
         "자료 요약. HTML 엔티티 혼입되어 정제 대상", "분석확인"),
        ("URL", "상세링크", "가공", "VARCHAR2",
         "EIEC 상세페이지 주소", "조인정의"),
        ("PUBLISH_DATE", "발간일자", "EPIC.ECO_POLICY_INFO.PUBLISH_DATE", "CHAR(8)",
         "YYYYMMDD 문자열", "스키마주석"),
        ("TOPIC", "토픽", "EPIC.ECO_POLICY_INFO_TOPIC.TOPIC", "VARCHAR2(4)",
         "토픽 코드. 자료당 복수 가능하여 쉼표로 연결. P = EPTS 등록 대상", "분석확인"),
        ("SUBJECT_NAME1", "주제명 1", "EPIC.JUJEDBE.J_NAME", "VARCHAR2(50)",
         "주제코드 1의 명칭", "분석확인"),
        ("매핑대상_대분류1", "매핑대상 대분류 1", "EPTS.CMTN_RELT_THEM_MNG", "VARCHAR2",
         "주제 1이 대응되는 EPTS 테마 대분류", "조인정의"),
        ("매핑대상_중분류1", "매핑대상 중분류 1", "〃", "VARCHAR2",
         "주제 1의 EPTS 테마 중분류", "조인정의"),
        ("매핑대상_소분류1", "매핑대상 소분류 1", "〃", "VARCHAR2",
         "주제 1의 EPTS 테마 소분류. 대책 매칭의 핵심 키", "조인정의"),
        ("부처", "부처", "PUBLISHER1 파생", "VARCHAR2",
         "PUBLISHER1의 첫 토큰. 예: 과학기술정보통신부", "조인정의"),
        ("등록대상", "등록 대상 여부", "TOPIC 파생", "BOOL",
         "TOPIC에 P가 포함되면 EPTS 등록 대상", "조인정의"),
    ],
    EPTS: [
        ("CTE_SEQ", "대책 순번", "EPTS.CMTN_CTE_MNG.CTE_SEQ", "NUMBER",
         "대책 고유키", "스키마주석"),
        ("CTE_NM", "대책명", "EPTS.CMTN_CTE_MNG.CTE_NM", "VARCHAR2(500)",
         "대책 명칭", "스키마주석"),
        ("CTE_USE_YN", "사용 여부", "EPTS.CMTN_CTE_MNG.USE_YN", "VARCHAR2(1)",
         "대책 사용 여부 Y/N. 기본값 Y", "스키마주석"),
        ("발표일자", "발표 일자", "EPTS.CMTN_CTE_MNG.PRST_DT", "VARCHAR2",
         "대책 발표 일자", "스키마주석"),
        ("소관부처_대", "소관부처", "EPTS.CMTN_CTE_MNG.GVDPT_BIG_NM", "VARCHAR2",
         "대책 소관부처 대분류명", "스키마주석"),
        ("테마_소분류1", "테마 소분류 1", "EPTS.CMTN_RELT_THEM_MNG", "VARCHAR2",
         "대책 관련테마 소분류명. EPIC 매핑대상 소분류와 대조", "스키마주석"),
        ("정책배경", "정책 배경", "EPTS.CMTN_CTE_MNG.POLC_BAKGRD_DESC_CONT", "CLOB",
         "정책 배경 설명. 웹에디터 HTML 원문이라 정제 대상", "스키마주석"),
        ("정책내용", "정책 내용", "EPTS.CMTN_CTE_MNG.CONT", "CLOB",
         "대책 내용. 웹에디터 HTML 원문이라 정제 대상", "스키마주석"),
        ("추진내역_건수", "추진내역 건수", "EPTS.CMTN_FRWD_HIST 집계", "NUMBER",
         "대책에 달린 추진내역 수", "조인정의"),
        ("매칭_EPIC수", "매칭 EPIC 수", "CMTN_CTE_MNG_EPIC_MPPG 집계", "NUMBER",
         "대책 본체에 연결된 자료 수", "조인정의"),
        ("포워딩_EPIC수", "포워딩 EPIC 수", "CMTN_FRWD_HIST_EPIC_MPPG 집계", "NUMBER",
         "추진내역에 연결된 자료 수", "조인정의"),
    ],
    LINK: [
        ("NUM", "자료 일련번호", "매핑 테이블", "NUMBER", "EPIC 자료 키", "스키마주석"),
        ("CTE_SEQ", "대책 순번", "매핑 테이블", "NUMBER", "EPTS 대책 키", "스키마주석"),
        ("관계구분", "관계 구분", "쿼리 파생", "VARCHAR2",
         "매칭 = 대책 본체 연결 / 포워딩 = 추진내역 연결", "조인정의"),
        ("FRWD_HIST_SEQ", "추진내역 순번", "CMTN_FRWD_HIST_EPIC_MPPG", "NUMBER",
         "포워딩일 때만 값이 있음", "스키마주석"),
        ("추진내역명", "추진내역명", "CMTN_FRWD_HIST.FRWD_HIST_NM", "VARCHAR2",
         "포워딩된 추진내역의 제목", "스키마주석"),
        ("대표노출여부", "대표 노출 여부", "MAIN_EXPSE_YN", "VARCHAR2(1)",
         "해당 대책의 대표 자료인지 Y/N", "스키마주석"),
    ],
}
