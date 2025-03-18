from databricks.sdk import AccountClient
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.iam import Group, ComplexValue, Patch, PatchSchema, PatchOp


w = WorkspaceClient()

host = 'https://accounts.cloud.databricks.com'
account_id = "0d26daa6-5e44-4c97-a497-ef015f91254a" # databricks account id
client_id = "a8c4d92d-1961-4249-ab45-2949534b4838" # client id of a service principal(having admin permission)
dbutils = w.dbutils

# Secret 조회
client_secret = dbutils.secrets.get(scope="one-env-hurcy-secret-scope",
                                    key="client_secret")
a = AccountClient(host=host,
                  account_id=account_id,
                  client_id=client_id,
                  client_secret=client_secret)

hurcy_ws = None
for w in a.workspaces.list():
    if w.deployment_name == 'one-env-hurcy':
        hurcy_ws = w

w = a.get_workspace_client(hurcy_ws)
print(w.current_user.me().active)

def update_group_members(group_id: str, members: list):
    """검색 결과[11]의 PATCH API 규격을 반영한 멤버 업데이트"""
    operations = []
    
    for member in members:
        op = Patch(
            op=PatchOp.ADD,
            value={ "members": [
                {
                "value":"cinyoung.hur@databricks.com"
                },
                {
                "value":"hurcy-sp"
                }
            ]}
        )
        operations.append(op)
    
    # 검색 결과[10]의 groups.update() 사용
    if members:
        a.groups.patch(
            id=group_id,
            operations=operations,
            schemas=[PatchSchema.URN_IETF_PARAMS_SCIM_API_MESSAGES_2_0_PATCH_OP]
        )

# 그룹 생성 및 구성
group_configs = [
    {
        "name": "Data Engineering Team",
        "members": ["cinyoung.hur@databricks.com", "hurcy-sp"],
        "roles": ["account_admin"]
    },
    {
        "name": "DS Team",
        "entitlements": ["allow-cluster-create"]
    }
]

for config in group_configs:
    # 1. 그룹 생성 (검색 결과[13] 참조)
    group = a.groups.create(display_name=config["name"])
    # w.workspace
    # 2. 멤버 일괄 추가
    # update_group_members(group.id, config.get("members", []))
    
    # # 3. 역할 및 권한 부여
    # for role in config.get("roles", []):
    #     w.groups.add_role(group.id, role)
    # for entitlement in config.get("entitlements", []):
    #     w.groups.add_entitlement(group.id, entitlement)
