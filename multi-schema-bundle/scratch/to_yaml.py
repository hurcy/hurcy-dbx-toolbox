import csv
import yaml

def csv_to_yaml(csv_path, yaml_path):
    resources = {"resources": {"schemas": {}, "volumes": {}}}
    
    with open(csv_path, "r") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            # Schema 생성
            system_key = row["system"]
            resources["resources"]["schemas"][system_key] = {
                "catalog_name": f"{row['company']}_{row['business_unit']}_mig",
                "name": system_key,
                "comment": row["description"]
            }
            
            # Volume 생성
            volume_key = row["transfer_volume"]
            resources["resources"]["volumes"][volume_key] = {
                "catalog_name": f"{row['company']}_{row['business_unit']}_mig",
                "name": volume_key,
                "schema_name": system_key
            }
    
    with open(yaml_path, "w") as yaml_file:
        yaml.dump(resources, yaml_file, default_flow_style=False, sort_keys=False)

# 사용 예시
csv_to_yaml("input.csv", "../resources/multi_schema.yaml")
