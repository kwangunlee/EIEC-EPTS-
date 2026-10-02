-- =============================================================
-- [01] EPIC 정책자료 마스터  —  자료 1건 = 1행 (행 증식 없음)
--
--   · 대책(CTE) 조인을 하지 않는다 → NUM이 중복되지 않는다
--   · TOPIC은 자료당 여러 개일 수 있어 LISTAGG로 묶는다
--   · 본문(ABSTRACT)은 원문 그대로 추출한다. HTML 정제는 파이썬에서.
--
--   산출 → data/epic.csv
-- =============================================================
WITH rel_x AS (                            -- EPTS_RELATION 정규화(대/중/소 이름 + DEPTH3 I접두·연접 분해)
    SELECT TRIM(r.SUBJECT_CODE) AS J_CODE,
           b.RELT_THEM_NM  AS BIG_NM,
           mn.RELT_THEM_NM AS MID_NM,
           sm.RELT_THEM_NM AS SML_NM
    FROM   EIEC.EPTS_RELATION r
    LEFT JOIN EPTS.CMTN_RELT_THEM_MNG b  ON b.RELT_THEM_CD  = r.EPTS_DEPTH1
    LEFT JOIN EPTS.CMTN_RELT_THEM_MNG mn ON mn.RELT_THEM_CD = r.EPTS_DEPTH2
    LEFT JOIN (SELECT LEVEL n FROM DUAL CONNECT BY LEVEL <= 10) lv
           ON lv.n <= REGEXP_COUNT(r.EPTS_DEPTH3, 'RELT_THEM[0-9]+')
    LEFT JOIN EPTS.CMTN_RELT_THEM_MNG sm
           ON sm.RELT_THEM_CD = REGEXP_SUBSTR(r.EPTS_DEPTH3,'RELT_THEM[0-9]+',1,lv.n)
),
code_big AS ( SELECT J_CODE, LISTAGG(NM,', ') WITHIN GROUP (ORDER BY NM) EPTS_BIG
              FROM (SELECT DISTINCT J_CODE, BIG_NM NM FROM rel_x WHERE BIG_NM IS NOT NULL) GROUP BY J_CODE ),
code_mid AS ( SELECT J_CODE, LISTAGG(NM,', ') WITHIN GROUP (ORDER BY NM) EPTS_MID
              FROM (SELECT DISTINCT J_CODE, MID_NM NM FROM rel_x WHERE MID_NM IS NOT NULL) GROUP BY J_CODE ),
code_sml AS ( SELECT J_CODE, LISTAGG(NM,', ') WITHIN GROUP (ORDER BY NM) EPTS_SML
              FROM (SELECT DISTINCT J_CODE, SML_NM NM FROM rel_x WHERE SML_NM IS NOT NULL) GROUP BY J_CODE ),
code_map AS (
    SELECT COALESCE(cb.J_CODE, cm.J_CODE, cs.J_CODE) AS J_CODE,
           cb.EPTS_BIG, cm.EPTS_MID, cs.EPTS_SML
    FROM      code_big cb
    FULL JOIN code_mid cm ON cm.J_CODE = cb.J_CODE
    FULL JOIN code_sml cs ON cs.J_CODE = COALESCE(cb.J_CODE, cm.J_CODE)
),
topic_a AS (                               -- 토픽 → 자료 단위 집계 (행 증식 제거)
    SELECT NUM,
           LISTAGG(TOPIC, ',') WITHIN GROUP (ORDER BY TOPIC) AS TOPIC_LIST,
           COUNT(*) AS TOPIC_CNT
    FROM   EPIC.ECO_POLICY_INFO_TOPIC
    GROUP  BY NUM
)
SELECT
    e.NUM,
    e.PUBLISHER1,
    e.TITLE,
    e.ABSTRACT,
    'https://eiec.kdi.re.kr/policy/materialView.do?num=' || e.NUM AS URL,
    e.PUBLISH_DATE,
    ta.TOPIC_LIST AS TOPIC,
    -- 주제는 코드·명칭을 쌍으로 내보낸다 (매칭은 코드, 표시는 한글명)
    TRIM(e.SUBJECT_CODE1) AS SUBJECT_CODE1,
    TRIM(e.SUBJECT_CODE2) AS SUBJECT_CODE2,
    TRIM(e.SUBJECT_CODE3) AS SUBJECT_CODE3,
    j1.J_NAME AS SUBJECT_NAME1,
        cm1.EPTS_BIG AS 매핑대상_대분류1, cm1.EPTS_MID AS 매핑대상_중분류1, cm1.EPTS_SML AS 매핑대상_소분류1,
    j2.J_NAME AS SUBJECT_NAME2,
        cm2.EPTS_BIG AS 매핑대상_대분류2, cm2.EPTS_MID AS 매핑대상_중분류2, cm2.EPTS_SML AS 매핑대상_소분류2,
    j3.J_NAME AS SUBJECT_NAME3,
        cm3.EPTS_BIG AS 매핑대상_대분류3, cm3.EPTS_MID AS 매핑대상_중분류3, cm3.EPTS_SML AS 매핑대상_소분류3
FROM EPIC.ECO_POLICY_INFO e
LEFT JOIN topic_a ta      ON ta.NUM = e.NUM
LEFT JOIN EPIC.JUJEDBE j1 ON j1.J_CODE = TRIM(e.SUBJECT_CODE1)
LEFT JOIN EPIC.JUJEDBE j2 ON j2.J_CODE = TRIM(e.SUBJECT_CODE2)
LEFT JOIN EPIC.JUJEDBE j3 ON j3.J_CODE = TRIM(e.SUBJECT_CODE3)
LEFT JOIN code_map cm1 ON cm1.J_CODE = TRIM(e.SUBJECT_CODE1)
LEFT JOIN code_map cm2 ON cm2.J_CODE = TRIM(e.SUBJECT_CODE2)
LEFT JOIN code_map cm3 ON cm3.J_CODE = TRIM(e.SUBJECT_CODE3)
WHERE e.PUBLISH_DATE >= '20260101'          -- ← 추출 기간. 필요에 맞게 조정
ORDER BY e.PUBLISH_DATE DESC, e.NUM DESC;
