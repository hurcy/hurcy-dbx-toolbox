from databricks.sdk import WorkspaceClient

# WorkspaceClient 초기화
w = WorkspaceClient()

# Secret Scope 생성
scope_name = "one-env-hurcy-secret-scope"
w.secrets.create_scope(scope=scope_name)

# 단일 라인 Secret 등록
w.secrets.put_secret(
    scope=scope_name,
    key="client_secret",
    string_value="token"
)
