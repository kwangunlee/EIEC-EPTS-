"""테스트용 합성 데이터 생성 — 실데이터의 특성(HTML 오염·행 증식·미등록)을 재현."""
import json, random, sys
from pathlib import Path
import pandas as pd

random.seed(42)
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "data")
OUT.mkdir(parents=True, exist_ok=True)

MIN = ["고용노동부", "기획재정부", "과학기술정보통신부", "개인정보보호위원회",
       "행정안전부", "금융위원회", "보건복지부"]
SUB = ["노동정책실 노동정책관 임금근로시간정책과", "예산실 예산총괄심의관",
       "연구개발정책실 미래인재정책국 미래인재정책과", "개인정보정책국 자율보호정책과"]
THEME = [("고용노동","고용안전망","퇴직연금"), ("재정/조세","재정","예산(안)"),
         ("과학기술/정보통신","소프트웨어","정보보호"), ("보건복지/교육","보건복지일반","보건복지정책")]
WORDS = ["퇴직연금 실물이전", "예산 편성지침", "정보보호 강화", "인재양성 확대",
         "고용안전망 확충", "디지털 전환 지원", "사회보장 개편"]

def dirty(s):   # 실제 DB처럼 HTML 엔티티로 오염시킴
    return (s.replace("(", "&#40;").replace(")", "&#41;")
             .replace("·", "&middot;").replace("→", "&rarr;"))

epic = []
for i in range(300):
    m = random.choice(MIN); t = random.choice(THEME); w = random.choice(WORDS)
    num = 285000 + i
    topics = random.choice(["P", "P", "P", "C", "P,C", "p", ""])
    epic.append({
        "NUM": str(num),
        "PUBLISHER1": f"{m} {random.choice(SUB)}",
        "TITLE": dirty(f"{w} 추진계획(안) 발표"),
        "ABSTRACT": dirty(f"{m}는 {w} 관련 제도개선을 추진한다. 주요 내용은 "
                          f"대상 확대 · 절차 간소화 → 체감도 제고이다."),
        "URL": f"https://eiec.kdi.re.kr/policy/materialView.do?num={num}",
        "PUBLISH_DATE": f"2026{random.randint(1,8):02d}{random.randint(1,28):02d}",
        "TOPIC": topics,
        "SUBJECT_NAME1": t[2], "매핑대상_대분류1": t[0],
        "매핑대상_중분류1": t[1], "매핑대상_소분류1": t[2],
        "SUBJECT_NAME2": None, "매핑대상_대분류2": None,
        "매핑대상_중분류2": None, "매핑대상_소분류2": None,
        "SUBJECT_NAME3": None, "매핑대상_대분류3": None,
        "매핑대상_중분류3": None, "매핑대상_소분류3": None,
    })

epts = []
for j in range(40):
    t = random.choice(THEME); w = random.choice(WORDS)
    epts.append({
        "CTE_SEQ": str(83500 + j),
        "CTE_NM": dirty(f"{w} 대책"),
        "CTE_USE_YN": random.choice(["Y","Y","Y","N"]),
        "발표일자": f"2026{random.randint(1,8):02d}01",
        "소관부처_대": random.choice(MIN), "소관부처_중": None, "소관부처_소": None,
        "테마_대분류1": t[0], "테마_중분류1": t[1], "테마_소분류1": t[2],
        "테마_대분류2": None, "테마_중분류2": None, "테마_소분류2": None,
        "테마_대분류3": None, "테마_중분류3": None, "테마_소분류3": None,
        "정책배경": ('&lt;p&gt;&lt;span style=&#34;font-weight:bold&#34;&gt;&#60;추진목표&#62;'
                  '&lt;/span&gt;&lt;/p&gt;&lt;ul&gt;&lt;li class=&#34;font-claude-response-body&#34;&gt;'
                  f'&#9312; {w} 기반 확충&lt;/li&gt;&lt;/ul&gt;') if j % 5 else '&lt;p&gt;&lt;br&gt;&lt;/p&gt;',
        "정책내용": f'&lt;p&gt;{w} 관련 연 3&#37; 수준&middot; 단계적 확대 &rarr; 추진&lt;/p&gt;',
        "평가내용": None, "대책설명": None,
        "추진내역_건수": random.randint(0,5),
        "추진내역_최종수정": None,
        "매칭_EPIC수": 0, "포워딩_EPIC수": 0,
        "조회수": random.randint(0,500), "등록일시": None, "수정일시": None,
    })

link = []
for e in random.sample(epic, 90):
    c = random.choice(epts)
    link.append({"NUM": e["NUM"], "CTE_SEQ": c["CTE_SEQ"], "관계구분": "매칭",
                 "FRWD_HIST_SEQ": None, "추진내역명": None,
                 "대표노출여부": random.choice(["Y","N"]), "순서": "1",
                 "등록일시": None, "수정일시": None})
for e in random.sample(epic, 40):
    c = random.choice(epts)
    link.append({"NUM": e["NUM"], "CTE_SEQ": c["CTE_SEQ"], "관계구분": "포워딩",
                 "FRWD_HIST_SEQ": "1", "추진내역명": dirty("1차 추진내역(안)"),
                 "대표노출여부": "N", "순서": "1", "등록일시": None, "수정일시": None})

# 저장 전에 정제 적용 (관리자 페이지가 하는 일과 동일)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import clean
for name, rows in (("epic", epic), ("epts", epts), ("link", link)):
    df = clean.clean_frame(pd.DataFrame(rows), maxlen=1000)
    df.to_csv(OUT / f"{name}.csv", index=False, encoding="utf-8-sig")

(OUT / "manifest.json").write_text(json.dumps({
    "생성일시": "2026-10-02 10:30", "작성자": "테스트",
    "비고": "합성 샘플 데이터",
    "건수": {"epic": len(epic), "epts": len(epts), "link": len(link)},
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"생성: epic {len(epic)} / epts {len(epts)} / link {len(link)} → {OUT}")
