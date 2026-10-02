-- =============================================================
-- [04] EIEC/EPIC 주제 체계  —  주제코드 1건 = 1행
--
--   ⚠ 계층 구조는 '추정'이다. EPIC.JUJEDBE에는 부모 컬럼이 없고
--     J_CODE 5자리(예: C0501)만 있다. 자리수로 계층을 유도했다.
--       대분류 = SUBSTR(J_CODE,1,1)   예) C
--       중분류 = SUBSTR(J_CODE,1,3)   예) C05
--       소분류 = J_CODE               예) C0501
--     O_JUJEDBE(O_CODE 3자리)가 중분류명으로 보여 조인했으나 미확정.
--     ↓ 파일 하단 [확인] 쿼리를 먼저 돌려 구조를 확정할 것.
--
--   매칭·검토는 코드로 하고, 화면 표시는 반드시 한글명을 쓴다.
--   그래서 코드와 명칭을 항상 쌍으로 내보낸다.
--
--   산출 → data/subject_eiec.csv
-- =============================================================
SELECT
    j.J_CODE                      AS 주제코드,        -- 소분류 코드 (매칭 기준)
    j.J_NAME                      AS 주제명,          -- 화면 표시용 한글명
    SUBSTR(j.J_CODE, 1, 1)        AS 대분류코드,
    SUBSTR(j.J_CODE, 1, 3)        AS 중분류코드,
    o.O_NAME                      AS 중분류명,        -- ⚠ 추정 (O_JUJEDBE 조인)
    ts.NAME                       AS 총괄주제명,      -- ⚠ 참고 (TOTAL_SUBJECT 동일코드)
    CASE WHEN j.J_CODE = '00000' THEN 'N' ELSE 'Y' END AS 유효여부,
    -- 이 주제코드가 EPTS 테마에 매핑돼 있는지
    CASE WHEN r.SUBJECT_CODE IS NULL THEN 'N' ELSE 'Y' END AS 매핑여부
FROM       EPIC.JUJEDBE j
LEFT JOIN  EPIC.O_JUJEDBE o
       ON  o.O_CODE = SUBSTR(j.J_CODE, 1, 3)
LEFT JOIN  EPIC.TOTAL_SUBJECT ts
       ON  ts.CODE = j.J_CODE
LEFT JOIN  (SELECT DISTINCT TRIM(SUBJECT_CODE) AS SUBJECT_CODE
            FROM   EIEC.EPTS_RELATION) r
       ON  r.SUBJECT_CODE = TRIM(j.J_CODE)
ORDER BY j.J_CODE;


-- =============================================================
-- [확인 1] 대분류 코드 체계 — 첫 글자별 분포와 예시
--   첫 글자가 실제로 대분류인지, 몇 종인지 확인한다.
-- =============================================================
-- SELECT SUBSTR(J_CODE,1,1) AS 대분류코드,
--        COUNT(*)           AS 주제수,
--        LISTAGG(J_NAME, ', ') WITHIN GROUP (ORDER BY J_CODE) AS 예시
-- FROM   EPIC.JUJEDBE
-- WHERE  J_CODE <> '00000'
-- GROUP  BY SUBSTR(J_CODE,1,1)
-- ORDER  BY 1;

-- =============================================================
-- [확인 2] O_JUJEDBE가 중분류 마스터가 맞는지
--   O_CODE가 J_CODE 앞 3자리와 일치하는 비율을 본다.
-- =============================================================
-- SELECT o.O_CODE, o.O_NAME,
--        (SELECT COUNT(*) FROM EPIC.JUJEDBE j
--          WHERE SUBSTR(j.J_CODE,1,3) = o.O_CODE) AS 하위주제수
-- FROM   EPIC.O_JUJEDBE o
-- ORDER  BY o.O_CODE;

-- =============================================================
-- [확인 3] 자리수 가정이 깨지는 코드가 있는지
-- =============================================================
-- SELECT J_CODE, J_NAME, LENGTH(J_CODE) AS 길이
-- FROM   EPIC.JUJEDBE
-- WHERE  NOT REGEXP_LIKE(J_CODE, '^[A-Z][0-9]{4}$')
-- ORDER  BY J_CODE;
