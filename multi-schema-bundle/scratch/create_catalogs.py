# import csv
# import subprocess

# def create_catalogs(csv_path):
#     with open(csv_path, 'r') as file:
#         reader = csv.DictReader(file)
#         for row in reader:
#             catalog_name = f"{row['company']}_{row['business_unit']}_mig"
#             cmd = [
#                 'databricks', 'catalogs', 'create',
#                 catalog_name,
#                 '--comment', row['description'],
#                 '--storage-root', f's3://hurcy-rootbucket/{catalog_name}'
#             ]
#             result = subprocess.run(
#                 cmd, 
#                 capture_output=True,
#                 text=True
#             )
#             if result.returncode == 0:
#                 print(f"Created: {catalog_name}")
#             else:
#                 print(f"Error[{result.returncode}]: {result.stderr}")

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
