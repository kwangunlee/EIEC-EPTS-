-- =============================================================
-- [03] EPIC ↔ EPTS 연결관계  —  NUM × CTE_SEQ × 관계구분 1건 = 1행
--
--   EPIC↔CTE는 매칭·포워딩 양방향 모두 M:N이다.
--   관계를 별도 테이블로 분리해야 01·02의 행 증식이 사라진다.
--
--   관계구분
--     매칭   : CMTN_CTE_MNG_EPIC_MPPG       (대책 본체 ↔ 자료)
--     포워딩 : CMTN_FRWD_HIST_EPIC_MPPG     (대책 추진내역 ↔ 자료)
--
--   산출 → data/link.csv
-- =============================================================
SELECT
    m.NUM,
    m.CTE_SEQ,
    '매칭'              AS 관계구분,
    NULL                AS FRWD_HIST_SEQ,
    NULL                AS 추진내역명,
    m.MAIN_EXPSE_YN     AS 대표노출여부,
    m.ORDR              AS 순서,
    m.REG_DTTM          AS 등록일시,
    m.MDFY_DTTM         AS 수정일시
FROM EPTS.CMTN_CTE_MNG_EPIC_MPPG m

UNION ALL

SELECT
    f.NUM,
    f.CTE_SEQ,
    '포워딩'            AS 관계구분,
    f.FRWD_HIST_SEQ,
    h.FRWD_HIST_NM      AS 추진내역명,
    f.MAIN_EXPSE_YN     AS 대표노출여부,
    f.ORDR              AS 순서,
    f.REG_DTTM          AS 등록일시,
    f.MDFY_DTTM         AS 수정일시
FROM EPTS.CMTN_FRWD_HIST_EPIC_MPPG f
LEFT JOIN EPTS.CMTN_FRWD_HIST h
       ON h.CTE_SEQ = f.CTE_SEQ
      AND h.FRWD_HIST_SEQ = f.FRWD_HIST_SEQ

ORDER BY NUM DESC, CTE_SEQ, 관계구분;
