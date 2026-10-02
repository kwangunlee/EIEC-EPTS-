-- =============================================================
-- [05] EPTS 테마(주제) 체계  —  테마코드 1건 = 1행
--
--   CMTN_RELT_THEM_MNG는 HRNK_RELT_THEM_CD로 부모를 가리키는
--   자기참조 트리다. CONNECT BY로 깊이·경로를 펼친다.
--
--   깊이 1 = 대분류 / 2 = 중분류 / 3 = 소분류
--   각 단계의 '코드'와 '한글명'을 모두 내보낸다
--   (매칭은 코드로, 표시는 한글명으로 하기 위함).
--
--   산출 → data/subject_epts.csv
-- =============================================================
WITH tree AS (
    SELECT
        RELT_THEM_CD                                   AS 테마코드,
        RELT_THEM_NM                                   AS 테마명,
        HRNK_RELT_THEM_CD                              AS 상위코드,
        USE_YN,
        ORDR,
        LEVEL                                          AS 깊이,
        SYS_CONNECT_BY_PATH(RELT_THEM_CD, '>')         AS 코드경로,
        SYS_CONNECT_BY_PATH(RELT_THEM_NM, ' > ')       AS 이름경로
    FROM   EPTS.CMTN_RELT_THEM_MNG
    START WITH HRNK_RELT_THEM_CD IS NULL
            OR HRNK_RELT_THEM_CD NOT IN (SELECT RELT_THEM_CD FROM EPTS.CMTN_RELT_THEM_MNG)
    CONNECT BY NOCYCLE PRIOR RELT_THEM_CD = HRNK_RELT_THEM_CD
)
SELECT
    테마코드,
    테마명,
    상위코드,
    깊이,
    CASE 깊이 WHEN 1 THEN '대분류' WHEN 2 THEN '중분류'
              WHEN 3 THEN '소분류' ELSE '깊이' || 깊이 END AS 계층,
    -- 경로에서 단계별 코드·이름을 분해 (앞의 '>' 때문에 n+1번째를 집는다)
    REGEXP_SUBSTR(코드경로,  '[^>]+', 1, 1) AS 대분류코드,
    REGEXP_SUBSTR(이름경로, '[^>]+', 1, 1) AS 대분류명,
    REGEXP_SUBSTR(코드경로,  '[^>]+', 1, 2) AS 중분류코드,
    REGEXP_SUBSTR(이름경로, '[^>]+', 1, 2) AS 중분류명,
    REGEXP_SUBSTR(코드경로,  '[^>]+', 1, 3) AS 소분류코드,
    REGEXP_SUBSTR(이름경로, '[^>]+', 1, 3) AS 소분류명,
    이름경로,
    USE_YN AS 사용여부,
    ORDR   AS 순서
FROM tree
ORDER BY 코드경로;


-- =============================================================
-- [확인] 최상위(루트) 노드가 제대로 잡혔는지
--   START WITH 조건이 맞지 않으면 트리가 비거나 중복된다.
-- =============================================================
-- SELECT COUNT(*) AS 전체테마,
--        SUM(CASE WHEN HRNK_RELT_THEM_CD IS NULL THEN 1 ELSE 0 END) AS 부모없음,
--        SUM(CASE WHEN HRNK_RELT_THEM_CD = RELT_THEM_CD THEN 1 ELSE 0 END) AS 자기참조
-- FROM   EPTS.CMTN_RELT_THEM_MNG;

-- [확인] 부모 코드가 마스터에 없는 고아 노드
-- SELECT c.RELT_THEM_CD, c.RELT_THEM_NM, c.HRNK_RELT_THEM_CD
-- FROM   EPTS.CMTN_RELT_THEM_MNG c
-- WHERE  c.HRNK_RELT_THEM_CD IS NOT NULL
--   AND  NOT EXISTS (SELECT 1 FROM EPTS.CMTN_RELT_THEM_MNG p
--                     WHERE p.RELT_THEM_CD = c.HRNK_RELT_THEM_CD);
