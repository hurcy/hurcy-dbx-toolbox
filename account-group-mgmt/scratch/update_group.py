from databricks.sdk import WorkspaceClient
from databricks.sdk.service.iam import Group, ComplexValue, Patch, PatchSchema, PatchOp

# SDK 클라이언트 초기화 (계정 레벨 권한 필요)
w = WorkspaceClient()

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
        w.groups.patch(
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
    group = w.groups.create(display_name=config["name"])
    
    # 2. 멤버 일괄 추가
    update_group_members(group.id, config.get("members", []))
    
    # # 3. 역할 및 권한 부여
    # for role in config.get("roles", []):
    #     w.groups.add_role(group.id, role)
    # for entitlement in config.get("entitlements", []):
    #     w.groups.add_entitlement(group.id, entitlement)
