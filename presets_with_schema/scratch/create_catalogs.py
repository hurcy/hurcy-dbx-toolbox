# # 실행 예시
import subprocess
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

def process_row(row):
    catalog_name = f"{row.company}_{row.business_unit}_mig"
    description = catalog_name
    try:
        subprocess.check_output([
            'databricks', 'catalogs', 'create',
            catalog_name,
            '--comment', description,
            '--storage-root', f's3://hurcy-rootbucket/{catalog_name}'
        ], stderr=subprocess.STDOUT)
        return (catalog_name, "SUCCESS")
    except subprocess.CalledProcessError as e:
        return (catalog_name, f"FAILED: {e.output.decode()}")

# 병렬 처리 실행
cols = ['company','business_unit']
df = pd.read_csv('input.csv')[cols].drop_duplicates()
with ThreadPoolExecutor(max_workers=5) as executor:
    results = executor.map(process_row, [row for _,row in df.iterrows()])

for catalog, status in results:
    print(f"{catalog.ljust(30)} | {status}")
