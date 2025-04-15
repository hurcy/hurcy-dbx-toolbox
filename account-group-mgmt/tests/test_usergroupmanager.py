import yaml
from databricks.sdk import AccountClient
from scratch.create_group import UserGroupManager
import pytest


@pytest.fixture
def manager():
    client = AccountClient()
    manager = UserGroupManager(client)
    return manager

@pytest.fixture
def yaml_data():
    yaml_file = 'scratch/org_chart.yaml'
    with open(yaml_file) as f:
        return yaml.safe_load(f)

def test_validate_structure(manager, yaml_data):
    
    report = manager.validate_structure(yaml_data["groups"])
    print("Validation Report:")
    print(f"Missing groups: {report['missing_groups']}")
    print(f"Extra groups: {report['extra_groups']}")
    print(f"Mismatched parents: {report['mismatched_parents']}")

def test_sync_structure(manager, yaml_data):
    yaml_data = yaml.safe_load(f)
    manager.sync_structure(yaml_data["groups"])
    print("Synchronization completed successfully")
