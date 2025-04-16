import yaml
from databricks.sdk import AccountClient
from scratch.user_group_sync import UserGroupManager
from pathlib import Path
import pytest


@pytest.fixture
def manager():
    host = 'https://accounts.cloud.databricks.com'
    account_id = "0d26daa6-5e44-4c97-a497-ef015f91254a" # databricks account id
    client_id = "a8c4d92d-1961-4249-ab45-2949534b4838" # client id of a service principal(having admin permission)
    client_secret = "please replace secret"
    client = AccountClient(host=host,
                            account_id=account_id,
                            client_id=client_id,
                            client_secret=client_secret)
    manager = UserGroupManager(client)
    return manager

@pytest.fixture
def yaml_data():
    
    yaml_file = Path(__file__).parent.parent.resolve() / 'scratch/org_chart.yaml'
    with open(yaml_file) as f:
        return yaml.safe_load(f)

def test_validate_structure(manager, yaml_data):
    
    report = manager.validate_structure(yaml_data["groups"])
    print("Validation Report:")
    print(f"Missing groups: {report['missing_groups']}")
    print(f"Extra groups: {report['extra_groups']}")
    print(f"Mismatched parents: {report['mismatched_parents']}")

def test_sync_structure(manager, yaml_data):
    manager.sync_structure(yaml_data["groups"])
    print("Synchronization completed successfully")
