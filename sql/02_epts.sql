-- =============================================================
-- [02] EPTS 대책 마스터  —  대책 1건 = 1행
--
--   · CMTN_CTE_MNG 기준이라 EPIC에 연결되지 않은 대책도 전부 나온다
--     (01 쿼리는 EPIC 기준 LEFT JOIN이라 연결된 대책만 보인다 — 기능2·3에 부족)
--   · 관련테마 3세트를 모두 이름으로 변환
--   · 본문(정책배경·정책내용)은 CLOB 원문 그대로. 정제는 파이썬에서.
--
--   산출 → data/epts.csv
-- =============================================================
WITH frwd_cnt AS (                          -- 대책별 추진내역 건수
    SELECT CTE_SEQ,
           COUNT(*) AS 추진내역_건수,
           MAX(MDFY_DTTM) AS 추진내역_최종수정
    FROM   EPTS.CMTN_FRWD_HIST
    GROUP  BY CTE_SEQ
),
link_cnt AS (                               -- 대책별 EPIC 연결 건수 (매칭 / 포워딩)
    SELECT CTE_SEQ,
           SUM(CASE WHEN SRC = 'M' THEN 1 ELSE 0 END) AS 매칭_EPIC수,
           SUM(CASE WHEN SRC = 'F' THEN 1 ELSE 0 END) AS 포워딩_EPIC수
    FROM (
        SELECT CTE_SEQ, NUM, 'M' AS SRC FROM EPTS.CMTN_CTE_MNG_EPIC_MPPG
        UNION ALL
        SELECT DISTINCT CTE_SEQ, NUM, 'F' FROM EPTS.CMTN_FRWD_HIST_EPIC_MPPG
    )
    GROUP BY CTE_SEQ
)
SELECT
    c.CTE_SEQ,
    c.CTE_NM,
    c.USE_YN                AS CTE_USE_YN,
    c.PRST_DT               AS 발표일자,
    c.GVDPT_BIG_NM          AS 소관부처_대,
    c.GVDPT_MID_NM          AS 소관부처_중,
    c.GVDPT_SML_NM          AS 소관부처_소,
    rb1.RELT_THEM_NM AS 테마_대분류1, rm1.RELT_THEM_NM AS 테마_중분류1, rs1.RELT_THEM_NM AS 테마_소분류1,
    rb2.RELT_THEM_NM AS 테마_대분류2, rm2.RELT_THEM_NM AS 테마_중분류2, rs2.RELT_THEM_NM AS 테마_소분류2,
    rb3.RELT_THEM_NM AS 테마_대분류3, rm3.RELT_THEM_NM AS 테마_중분류3, rs3.RELT_THEM_NM AS 테마_소분류3,
    c.POLC_BAKGRD_DESC_CONT AS 정책배경,
    c.CONT                  AS 정책내용,
    c.ASSM_CONT             AS 평가내용,
    c.CTE_DESC              AS 대책설명,
    NVL(fc.추진내역_건수, 0)   AS 추진내역_건수,
    fc.추진내역_최종수정,
    NVL(lc.매칭_EPIC수, 0)    AS 매칭_EPIC수,
    NVL(lc.포워딩_EPIC수, 0)  AS 포워딩_EPIC수,
    c.CTE_SRCH_CUNT         AS 조회수,
    c.REG_DTTM              AS 등록일시,
    c.MDFY_DTTM             AS 수정일시
FROM EPTS.CMTN_CTE_MNG c
LEFT JOIN frwd_cnt fc ON fc.CTE_SEQ = c.CTE_SEQ
LEFT JOIN link_cnt lc ON lc.CTE_SEQ = c.CTE_SEQ
LEFT JOIN EPTS.CMTN_RELT_THEM_MNG rb1 ON rb1.RELT_THEM_CD = c.RELT_THEM_BIG_1_CD
LEFT JOIN EPTS.CMTN_RELT_THEM_MNG rm1 ON rm1.RELT_THEM_CD = c.RELT_THEM_MID_1_CD
LEFT JOIN EPTS.CMTN_RELT_THEM_MNG rs1 ON rs1.RELT_THEM_CD = c.RELT_THEM_SML_1_CD
LEFT JOIN EPTS.CMTN_RELT_THEM_MNG rb2 ON rb2.RELT_THEM_CD = c.RELT_THEM_BIG_2_CD
LEFT JOIN EPTS.CMTN_RELT_THEM_MNG rm2 ON rm2.RELT_THEM_CD = c.RELT_THEM_MID_2_CD
LEFT JOIN EPTS.CMTN_RELT_THEM_MNG rs2 ON rs2.RELT_THEM_CD = c.RELT_THEM_SML_2_CD
LEFT JOIN EPTS.CMTN_RELT_THEM_MNG rb3 ON rb3.RELT_THEM_CD = c.RELT_THEM_BIG_3_CD
LEFT JOIN EPTS.CMTN_RELT_THEM_MNG rm3 ON rm3.RELT_THEM_CD = c.RELT_THEM_MID_3_CD
LEFT JOIN EPTS.CMTN_RELT_THEM_MNG rs3 ON rs3.RELT_THEM_CD = c.RELT_THEM_SML_3_CD
-- 미사용 대책까지 보려면 아래 줄을 주석 처리
-- WHERE c.USE_YN = 'Y'
ORDER BY c.CTE_SEQ DESC;
