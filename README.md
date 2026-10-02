# 정책정보허브 (EPIC ↔ EPTS 작업 지원)

KDI 경제정보센터 정책정보허브팀의 EPTS 등록·검토 업무를 돕는 Streamlit 앱.

데이터는 **관리자가 올린 스냅샷**을 팀원이 함께 본다. 각자 파일을 올리는 방식이 아니라,
`data/` 에 커밋된 한 벌을 모두가 보고, 화면 좌측에 **기준 시점**이 항상 표시된다.

---

## 구조

```
app.py                  라우팅만. 기능 추가 시 손대지 않는다
core/                   Streamlit에 의존하지 않는 순수 로직 (테스트 가능)
  schema.py             컬럼 정의·상수·컬럼정의서
  clean.py              HTML 정제 (노트북 로직 이식)
  transform.py          부처 추출, 등록여부 판정, 집계
  subject.py            주제 체계 분석 (코드 기준 매칭)
  loader.py             data/ 적재 + manifest + 검증
  recommend.py          기능3 추천 엔진
features/               기능(페이지) 모듈 — 하나당 파일 하나
  base.py               Page 인터페이스 + 공통 위젯
  registry.py           ★ 기능 등록부
  f1_registration.py    기능1 EPTS 등록 현황
  f2_epts_detail.py     기능2 EPTS 대책 상세
  f3_recommend.py       기능3 추진내역 추천
  f4_subject.py         기능4 주제분류 현황
  f9_admin.py           데이터 갱신 (관리자)
sql/                    추출 쿼리 6종
data/                   스냅샷 (epic.csv, epts.csv, link.csv, manifest.json)
tests/                  합성 데이터 생성 + 전 페이지 헤드리스 테스트
```

**계층 규칙** — `features/` 는 `core/` 를 호출한다. 반대 방향은 없다.
`core/` 에 Streamlit을 import하지 않는다. 그래야 로직을 단독으로 테스트할 수 있다.

---

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

데이터 없이도 뜬다. 각 기능이 "데이터가 필요합니다"라고 안내한다.
구경부터 하려면 합성 데이터를 만들면 된다.

```bash
python tests/make_sample.py data     # 가짜 데이터 300/40/130건 생성
```

> 합성 데이터는 실제 값이 아니다. 확인 후 `data/` 를 비우고 실데이터를 넣는다.

---

## 데이터 갱신 (관리자)

1. DBeaver에서 `sql/` 의 쿼리를 각각 실행해 **CSV로 내보낸다.**
   `01`~`03` 은 매번, `04`~`06`(주제 체계)은 분류 체계가 바뀔 때만 갱신하면 된다.
   - HTML 정제는 하지 않는다. 원문 그대로 받는다.
   - 내보내기 설정: 인코딩 `UTF-8`, **`Quote always` 켜기** (CLOB에 줄바꿈·쉼표가 들어 있다)
   - CLOB이 잘리면 Preferences → Editors → Data Editor → `Maximum LOB length` 를 키운다.
2. 앱의 **⚙️ 데이터 갱신** 에서 세 파일을 올린다. 정제·검증 결과를 확인한다.
3. `data 묶음 내려받기 (zip)` → 압축 해제 → 저장소 `data/` 에 덮어쓰기 → 커밋·푸시.
4. 팀원 화면의 **기준 시점**이 바뀐다.

Streamlit Cloud의 파일시스템은 휘발성이라 앱이 repo에 직접 쓰지 않는다. 커밋이 곧 배포다.

### 왜 쿼리가 3개인가

하나의 통합 쿼리는 `NUM × TOPIC × CTE_SEQ` 카티전으로 행이 불어난다.
자료 1건이 여러 행으로 쪼개지면 건수 집계가 전부 틀어진다.
그래서 **자료 / 대책 / 관계** 셋으로 정규화했다.

| 파일 | 기준 | 비고 |
|---|---|---|
| `epic.csv` | 자료 1건 = 1행 | TOPIC은 쉼표로 묶음 |
| `epts.csv` | 대책 1건 = 1행 | **EPIC에 연결 안 된 대책도 포함** |
| `link.csv` | NUM × CTE_SEQ × 관계구분 | 매칭 / 포워딩 구분 |
| `subject_eiec.csv` | EIEC 주제코드 1건 = 1행 | 계층은 코드 자리수로 추정 |
| `subject_epts.csv` | EPTS 테마코드 1건 = 1행 | `HRNK_RELT_THEM_CD` 트리 |
| `subject_map.csv` | 주제코드 × 테마코드 1쌍 = 1행 | `EPTS_RELATION` 전개 |

`epts.csv` 가 별도인 이유 — EPIC 기준 LEFT JOIN으로는 "연결된" 대책만 보인다.
기능 2·3은 연결이 **없는** 대책이 오히려 핵심 대상이다.

---

## 기능

### 1. EPTS 등록 현황
`TOPIC` 에 `P` 가 있는 자료가 대책에 등록됐는지 **부처별로** 점검한다.

- 부처 = `PUBLISHER1` 의 첫 토큰
  (`과학기술정보통신부 연구개발정책실 미래인재정책국 미래인재정책과` → `과학기술정보통신부`)
- 등록 판정은 **대책 본체 매칭** 기준. 포워딩만 있는 건은 미등록으로 본다.
- `TOPIC` 소문자 `p` 혼입(알려진 데이터 오류)은 대소문자 무시로 흡수한다.

### 2. EPTS 대책 상세
대책의 관련주제·정책배경·정책내용과, 연결된 EPIC을 매칭/포워딩으로 나눠 본다.
관련테마가 비어 있으면 경고한다 (추천 정확도가 떨어지므로).

### 4. 주제분류 현황
EIEC 주제와 EPTS 테마는 **서로 독립된 체계**다. 둘을 잇는 건 `EPTS_RELATION` 하나뿐이다.

| 체계 | 마스터 | 계층 |
|---|---|---|
| EIEC/EPIC | `EPIC.JUJEDBE` | 부모 컬럼 **없음**. `J_CODE` 자리수로 추정 (`C` / `C05` / `C0501`) |
| EPTS | `EPTS.CMTN_RELT_THEM_MNG` | `HRNK_RELT_THEM_CD` 자기참조 트리 |

**집계·매칭은 코드로, 표시는 한글명으로** 한다. 이름은 중복·변경되지만 코드는 안정적이다.
그래서 모든 주제 데이터셋은 코드와 명칭을 쌍으로 들고 다닌다.

탭 구성 — 매핑 현황(미매핑 주제를 자료 많은 순으로) / EIEC 주제 체계 / EPTS 테마 체계 /
정합성 점검(마스터에 없는 주제코드, 깨진 매핑).

> ⚠ EIEC 계층은 추정이다. `sql/04_subject_eiec.sql` 하단의 [확인] 쿼리로 체계를 확정한 뒤
> 실제와 다르면 쿼리를 고쳐야 한다.

### 3. 추진내역 추천
대책 내용을 질의로 삼아 붙을 만한 EPIC을 점수순으로 제시한다.

| 신호 | 가중치 | 근거 강도 |
|---|---|---|
| 소분류 일치 (EPIC 매핑대상 ∩ 대책 테마) | 3.0 | 강 — 코드 기반 |
| 중분류 일치 | 1.5 | 중 |
| 대분류 일치 | 0.7 | 약 |
| 키워드 유사도 (제목·초록 ↔ 대책명·배경·내용) | 2.0 × 코사인 | 보조 |

한국어 형태소 분석기 없이 **문자 n-gram TF-IDF**(`char_wb`, 2–3gram)를 쓴다.
외부 API·사전이 필요 없고 사내망에서도 돈다.
가중치는 `core/recommend.py` 의 `WEIGHTS` 에서 조정한다.

**추천은 추천일 뿐이다.** 연결 여부는 담당자가 판단한다.

---

## 기능 추가하는 법

전체를 고칠 일 없이 파일 하나 + 한 줄이면 된다.

1. `features/f4_xxx.py` 생성

```python
from core.loader import Bundle
from .base import Page, WIDE, need

def render(bundle: Bundle) -> None:
    if not need(bundle, "epic"):      # 필요한 데이터셋 선언
        return
    ...                                # 화면 구성

PAGE = Page(key="f4", label="새 기능", icon="📈", render=render,
            help="한 줄 설명")
```

2. `features/registry.py` 에 추가

```python
from . import f4_xxx
PAGES = [..., f4_xxx.PAGE]
```

`app.py` 는 건드리지 않는다.

**새 컬럼이 필요하면** `core/transform.py` 에 파생 함수를 추가하고
`loader.load_bundle()` 에서 호출한다. 화면 코드에 계산 로직을 넣지 않는다.

---

## 테스트

```bash
python tests/make_sample.py data     # 합성 데이터
python tests/test_app.py             # 전 페이지 헤드리스 실행
```

`test_app.py` 는 Streamlit `AppTest` 로 모든 페이지를 실제로 렌더링해 예외를 잡는다.
데이터가 없는 상태(새로 clone한 경우)도 통과해야 한다.

---

## 배포

데이터가 저장소에 들어가므로 **private 저장소를 권장한다.**
미사용(`USE_YN='N'`) 대책 등 미공개 상태의 내용이 포함될 수 있다.

- 사내 서버: `streamlit run app.py --server.port 8501 --server.address 0.0.0.0`
- Streamlit Community Cloud: 비공개 저장소 연결 가능 여부·한도는 계정 설정에서 확인이 필요하다.

---

## 알려진 데이터 이슈

| 이슈 | 현황 | 대응 |
|---|---|---|
| 본문 HTML 오염 | 웹에디터에 서식째 붙여넣기 → `&lt;p&gt;`, `font-claude-response-body` 등이 이스케이프되어 저장 | 조회 시 정제. **원본은 그대로** — 입력 단계 수정 필요 |
| 빈 껍데기 본문 | NULL이 아니라 `<p><br></p>` | 정제 후 빈칸 처리 |
| TOPIC 소문자 | `p` 혼입 | 대소문자 무시 |
| EIEC 주제 계층 | 마스터에 부모 컬럼 없음 | 코드 자리수로 추정 — `04` 쿼리 [확인] 필요 |
| DBeaver NULL 문자열 | `[NULL]` 등이 글자로 내보내짐 | `schema.NA_STRINGS` 로 환원 |

오염 건의 입력 경로는 아래로 추적한다.

```sql
SELECT CTE_SEQ, CTE_NM, MDFY_ID, MDFY_DTTM
FROM   EPTS.CMTN_CTE_MNG
WHERE  DBMS_LOB.INSTR(CONT, 'font-claude-response-body') > 0
   OR  DBMS_LOB.INSTR(POLC_BAKGRD_DESC_CONT, 'font-claude-response-body') > 0
ORDER  BY MDFY_DTTM DESC;
```

DB는 조회 전용으로 다룬다. 이 앱은 `INSERT`/`UPDATE`/`DELETE` 를 하지 않는다.
