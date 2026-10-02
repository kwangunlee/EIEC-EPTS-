-- =============================================================
-- [06] 주제 매핑  —  EIEC 주제코드 × EPTS 테마코드 1쌍 = 1행
--
--   EIEC.EPTS_RELATION이 두 체계를 잇는 유일한 테이블이다.
--     SUBJECT_CODE = EIEC/EPIC 주제코드 (J_CODE와 같은 형식, 예 E0201)
--     EPTS_DEPTH1/2/3 = EPTS 테마코드
--
--   ⚠ EPTS_DEPTH3는 'I' 접두와 연접이 섞여 있어 그대로 조인하면 안 된다.
--     REGEXP로 'RELT_THEM[0-9]+' 패턴만 뽑아 행으로 펼친다.
--     (실데이터 기준 한 셀 최대 3개 — CONNECT BY LEVEL <= 10으로 여유)
--
--   매칭은 코드로, 표시는 한글명으로 하므로 양쪽 모두 내보낸다.
--
--   산출 → data/subject_map.csv
-- =============================================================
WITH expanded AS (
    -- DEPTH1 (대) / DEPTH2 (중) 는 단일 코드
    SELECT TRIM(r.SUBJECT_CODE) AS 주제코드, '대분류' AS 매핑단계,
           TRIM(r.EPTS_DEPTH1)  AS 테마코드
    FROM   EIEC.EPTS_RELATION r
    WHERE  r.EPTS_DEPTH1 IS NOT NULL
    UNION ALL
    SELECT TRIM(r.SUBJECT_CODE), '중분류', TRIM(r.EPTS_DEPTH2)
    FROM   EIEC.EPTS_RELATION r
    WHERE  r.EPTS_DEPTH2 IS NOT NULL
    UNION ALL
    -- DEPTH3 (소) 는 연접·접두 분해 필요
    SELECT TRIM(r.SUBJECT_CODE), '소분류',
           REGEXP_SUBSTR(r.EPTS_DEPTH3, 'RELT_THEM[0-9]+', 1, lv.n)
    FROM   EIEC.EPTS_RELATION r
    JOIN   (SELECT LEVEL n FROM DUAL CONNECT BY LEVEL <= 10) lv
      ON   lv.n <= REGEXP_COUNT(r.EPTS_DEPTH3, 'RELT_THEM[0-9]+')
    WHERE  r.EPTS_DEPTH3 IS NOT NULL
)
SELECT DISTINCT
    e.주제코드,
    j.J_NAME            AS 주제명,          -- EIEC 쪽 한글명
    SUBSTR(e.주제코드, 1, 1) AS 주제_대분류코드,
    SUBSTR(e.주제코드, 1, 3) AS 주제_중분류코드,
    e.매핑단계,
    e.테마코드,
    t.RELT_THEM_NM      AS 테마명,          -- EPTS 쪽 한글명
    t.HRNK_RELT_THEM_CD AS 테마_상위코드,
    t.USE_YN            AS 테마_사용여부,
    CASE WHEN j.J_CODE IS NULL THEN 'Y' ELSE 'N' END AS 주제코드_미존재,
    CASE WHEN t.RELT_THEM_CD IS NULL THEN 'Y' ELSE 'N' END AS 테마코드_미존재
FROM       expanded e
LEFT JOIN  EPIC.JUJEDBE j
       ON  j.J_CODE = e.주제코드
LEFT JOIN  EPTS.CMTN_RELT_THEM_MNG t
       ON  t.RELT_THEM_CD = e.테마코드
WHERE  e.테마코드 IS NOT NULL
ORDER BY e.주제코드, e.매핑단계, e.테마코드;


-- =============================================================
-- [확인] 매핑 무결성 — 양쪽 마스터에 없는 코드가 있는지
--   위 결과의 주제코드_미존재 / 테마코드_미존재가 Y인 행이 깨진 매핑이다.
-- =============================================================
-- SELECT COUNT(DISTINCT TRIM(SUBJECT_CODE)) AS 매핑된_주제수,
--        (SELECT COUNT(*) FROM EPIC.JUJEDBE WHERE J_CODE <> '00000') AS 전체_주제수
-- FROM   EIEC.EPTS_RELATION;

-- [확인] DEPTH3 연접 최대 개수 — 10을 넘으면 CONNECT BY 한도를 올린다
-- SELECT MAX(REGEXP_COUNT(EPTS_DEPTH3, 'RELT_THEM[0-9]+')) AS 최대연접수
-- FROM   EIEC.EPTS_RELATION;
