import pandas as pd
from pyspark.sql import SparkSession
from delta.tables import DeltaTable
from hashlib import sha256

def generate_group_id(group_name):
    return f"GRP_{sha256(group_name.encode()).hexdigest()[:8]}"

spark = SparkSession.builder.getOrCreate()
delta_path = '/delta/groups'

# 계층 정보 캐시 딕셔너리 {group_id: (parent_id, hierarchy_path)}
group_cache = {}

# CSV 파일 읽기 (컬럼명 기반)
df = pd.read_csv('input.csv')
records = []

for _, row in df.iterrows():
    # 계층 구조 추출
    group1 = row['group1']
    group2 = row['group2']
    group3s = [row['group3_1'], row['group3_2'], row['group3_3']]

    # Group1 처리
    group1_id = generate_group_id(group1)
    if group1_id not in group_cache:
        hierarchy_path = f"/{group1_id}"
        records.append((group1_id, group1, None, hierarchy_path))
        group_cache[group1_id] = (None, hierarchy_path)

    # Group2 처리
    group2_id = generate_group_id(group2)
    if group2_id not in group_cache:
        parent_hpath = group_cache[group1_id][1]
        hierarchy_path = f"{parent_hpath}/{group2_id}"
        records.append((group2_id, group2, group1_id, hierarchy_path))
        group_cache[group2_id] = (group1_id, hierarchy_path)

    # Group3 처리
    for group3 in group3s:
        group3_id = generate_group_id(group3)
        if group3_id not in group_cache:
            parent_hpath = group_cache[group2_id][1]
            hierarchy_path = f"{parent_hpath}/{group3_id}"
            records.append((group3_id, group3, group2_id, hierarchy_path))
            group_cache[group3_id] = (group2_id, hierarchy_path)

# Spark DataFrame으로 변환 후 일괄 저장
if records:
    spark_df = spark.createDataFrame(
        records, 
        ["group_id", "group_name", "parent_id", "hierarchy_path"]
    )
    
    spark_df.write.format("delta") \
        .mode("append") \
        .save(delta_path)

# 테이블 최적화
spark.sql(f"OPTIMIZE delta.`{delta_path}` ZORDER BY (hierarchy_path)")
