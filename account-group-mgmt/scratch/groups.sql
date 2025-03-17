-- 관리형 Delta 테이블 생성
CREATE TABLE groups (
    group_id STRING,
    group_name STRING NOT NULL,
    parent_id STRING,
    hierarchy_path STRING
) USING DELTA
LOCATION '/delta/groups'
;
