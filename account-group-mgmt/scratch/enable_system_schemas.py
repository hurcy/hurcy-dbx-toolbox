from databricks.sdk import AccountClient
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import SystemSchemaInfo, SystemSchemaInfoState
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
assert w.current_user.me().active

metastore_id = None

for m in w.metastores.list():
    if m.name == 'hurcy-com-ap-northeast-2' and m.owner == 'cinyoung.hur@databricks.com':
        metastore_id = m.metastore_id

for s in w.system_schemas.list(metastore_id=metastore_id):
    if s.state == SystemSchemaInfoState.AVAILABLE:
        w.system_schemas.enable(metastore_id, s.schema)

