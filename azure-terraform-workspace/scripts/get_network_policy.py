"""
사전준비사항
- Azure Managed Identity 생성 및 Databricks Service Principal과 연결 (권장: MI로 Account API 토큰 획득)
- 또는 Databricks Service Principal의 client_id/secret을 환경변수로 부트스트랩
- Databricks Service Principal에 Account admin 권한 부여

Databricks Network Policy 정보 조회 및 이력 저장 스크립트 (REST API 버전)

인증 순서: (1) Azure Managed Identity로 Account API 토큰 획득 시도 (azure-identity 패키지 사용)
          (2) 실패 또는 미설치 시 환경변수 DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET 사용
          Databricks Job에서 MI 사용: docs/databricks-job-managed-identity.md 참고 (WIF 또는 VM+MI)

이 스크립트는 requests 모듈을 사용하여 REST API로:
0. (선택) Account API로 대상 Service Principal 조회 → OAuth 시크릿 생성 → DATABRICKS_CLIENT_ID/SECRET에 설정
1. 현재 워크스페이스에 설정된 network_policy_id를 획득
2. 해당 네트워크 정책의 상세 정보를 조회
3. SCD Type 1 패턴으로 Delta 테이블에 이력 저장 (변경 시에만)
4. (선택) 사용한 OAuth 시크릿 삭제

API 참고:
- https://docs.databricks.com/api/azure/account/workspacenetworkconfiguration/getworkspacenetworkoptionrpc
- https://docs.databricks.com/api/azure/account/networkpolicies/getnetworkpolicyrpc
- https://docs.databricks.com/api/azure/account/accountserviceprincipals/get
- https://docs.databricks.com/api/azure/account/serviceprincipalsecrets/create
- https://docs.databricks.com/api/azure/account/serviceprincipalsecrets/delete
"""

import json
import hashlib
import os
from datetime import datetime
from pprint import pprint
from typing import Optional

import requests
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, max as spark_max
from pyspark.sql.types import StructType, StructField, StringType, LongType, TimestampType, BooleanType

# =============================================================================
# Databricks Account 인증 정보 (상수)
# =============================================================================
DATABRICKS_HOST = "https://accounts.azuredatabricks.net"
DATABRICKS_ACCOUNT_ID = os.environ.get("DATABRICKS_ACCOUNT_ID", "")
# Azure Databricks 리소스 ID (MI 토큰 scope/audience). https://learn.microsoft.com/azure/databricks/dev-tools/auth/troubleshoot-aad-token
DATABRICKS_ARM_RESOURCE_ID = os.environ.get("DATABRICKS_ARM_RESOURCE_ID", "")
# 이 SP로 Databricks client id/secret 발급(시크릿 생성) 후 본 프로세스 실행, 완료 후 시크릿 삭제
SERVICE_PRINCIPAL_APPLICATION_ID = os.environ.get("SERVICE_PRINCIPAL_APPLICATION_ID", "")

# 부트스트랩(SP 조회/시크릿 생성·삭제) 시 사용. MI 우선, 미사용 시 환경변수. run_with_temporary_sp_credentials() 내부에서 SP 시크릿 발급 시 DATABRICKS_* 일시 덮어씀
DATABRICKS_CLIENT_ID = os.environ.get("DATABRICKS_CLIENT_ID", "")
DATABRICKS_CLIENT_SECRET = os.environ.get("DATABRICKS_CLIENT_SECRET", "")


# =============================================================================
# 조회할 워크스페이스 ID
# =============================================================================
WORKSPACE_ID = dbutils.notebook.entry_point.getDbutils().notebook().getContext().workspaceId().getOrElse(None)

# =============================================================================
# 이력 저장 테이블 (catalog.schema.table)
# =============================================================================
TARGET_TABLE = "hurcy_catalog.default.network_policy_history"

# Debug 모드: Job parameter(spark.conf job_parameter.debug) 또는 환경변수 DEBUG
# true/1 이면 debug 로그까지 출력
DEBUG_MODE = False


def _resolve_debug_mode(spark) -> bool:
    """Spark conf 또는 환경변수에서 debug 여부를 읽어 DEBUG_MODE를 설정하고 반환합니다."""
    global DEBUG_MODE
    try:
        val = spark.conf.get("job_parameter.debug", os.environ.get("DEBUG", "false"))
    except Exception:
        val = os.environ.get("DEBUG", "false")
    DEBUG_MODE = str(val).lower() in ("true", "1", "yes")
    return DEBUG_MODE


def log_info(msg: str) -> None:
    """요약/결과 등 정보 메시지 (항상 출력)."""
    print(msg)


def log_debug(msg: str) -> None:
    """상세 메시지 (debug 모드일 때만 출력)."""
    if DEBUG_MODE:
        print(msg)


def get_access_token_with(client_id: str, client_secret: str) -> str:
    """
    OAuth2 Client Credentials로 액세스 토큰을 획득합니다.
    (부트스트랩 또는 실행용 credentials 지정 가능)
    """
    token_url = f"{DATABRICKS_HOST}/oidc/accounts/{DATABRICKS_ACCOUNT_ID}/v1/token"
    response = requests.post(
        token_url,
        data={"grant_type": "client_credentials", "scope": "all-apis"},
        auth=(client_id, client_secret),
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_access_token() -> str:
    """
    OAuth2 Client Credentials를 사용하여 액세스 토큰을 획득합니다.
    (모듈 전역 DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET 사용)
    """
    return get_access_token_with(DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET)


def get_access_token_via_managed_identity(
    scope: Optional[str] = None,
    managed_identity_client_id: Optional[str] = None,
) -> Optional[str]:
    """
    Azure Managed Identity 또는 Workload Identity Federation(WIF)으로 Account API용 Bearer 토큰을 획득합니다.
    - WIF: Databricks Job(Shared/UC)에서 AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_FEDERATED_TOKEN_FILE 설정 시
    - MI: Azure VM 등 IMDS 사용 가능 환경에서 ManagedIdentityCredential 사용

    Args:
        scope: 토큰 scope. 기본값은 Azure Databricks 리소스 ID의 .default
        managed_identity_client_id: User-assigned MI 사용 시 client_id (None이면 env AZURE_CLIENT_ID 또는 system-assigned)

    Returns:
        액세스 토큰 문자열. 사용할 수 없거나 실패 시 None
    """
    try:
        from azure.identity import ManagedIdentityCredential, WorkloadIdentityCredential
    except ImportError:
        log_debug("azure-identity 미설치: Managed Identity/WIF 경로 비활성화. pip install azure-identity 권장.")
        return None

    if scope is None:
        scope = f"{DATABRICKS_ARM_RESOURCE_ID}/.default"

    # 1) WIF: Databricks Job(Shared/UC)에서 AZURE_* 세 개가 설정된 경우 WIF만 시도 (IMDS로 fallback 안 함)
    #    → Databricks에서는 IMDS가 없어서 fallback 시 항상 실패하므로, WIF 실패 시 명확한 오류만 반환
    token_file = os.environ.get("AZURE_FEDERATED_TOKEN_FILE")
    client_id = managed_identity_client_id or os.environ.get("AZURE_CLIENT_ID")
    tenant_id = os.environ.get("AZURE_TENANT_ID")
    wif_configured = token_file and client_id and tenant_id

    if wif_configured:
        if not os.path.isfile(token_file):
            log_info(
                f"[WIF] 토큰 파일이 없습니다: {token_file}. "
                "클러스터가 Shared(UC)이고, UAMI를 SP로 등록한 뒤 해당 클러스터에 Can Attach To 권한을 부여했는지 확인하세요. "
                "또는 부트스트랩용으로 DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET 환경변수를 사용하려면 "
                "AZURE_FEDERATED_TOKEN_FILE(또는 세 WIF 변수)을 설정하지 마세요."
            )
            return None
        try:
            wif_credential = WorkloadIdentityCredential(
                client_id=client_id,
                tenant_id=tenant_id,
                token_file_path=token_file,
            )
            token = wif_credential.get_token(scope)
            log_debug("Workload Identity Federation(WIF)으로 Account API 토큰 획득.")
            return token.token
        except Exception as e:
            log_info(f"[WIF] 토큰 획득 실패: {e}. Federated credential(Issuer/Subject/Audience) 및 UAMI 설정을 확인하세요.")
            return None

    # 2) MI: VM 등 IMDS 사용 가능 환경 (WIF env 미설정 시에만)
    try:
        credential = ManagedIdentityCredential(client_id=managed_identity_client_id) if managed_identity_client_id else ManagedIdentityCredential()
        token = credential.get_token(scope)
        log_debug("Managed Identity(IMDS)로 Account API 토큰 획득.")
        return token.token
    except Exception as e:
        log_debug(f"Managed Identity 토큰 획득 실패 (MI 미사용 환경이면 정상): {e}")
        return None


def get_service_principal(access_token: str, service_principal_id: str) -> dict:
    """
    Account 레벨에서 Service Principal 정보를 조회합니다.
    https://docs.databricks.com/api/azure/account/accountserviceprincipals/get

    Args:
        access_token: Account API용 Bearer 토큰
        service_principal_id: Service Principal ID (Azure에서는 application_id 사용)

    Returns:
        Service Principal 정보 딕셔너리
    """
    url = f"{DATABRICKS_HOST}/api/2.0/accounts/{DATABRICKS_ACCOUNT_ID}/servicePrincipals/{service_principal_id}"
    response = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    response.raise_for_status()
    return response.json()


def create_service_principal_secret(access_token: str, service_principal_id: str, comment: str = "") -> dict:
    """
    Service Principal용 OAuth 시크릿을 생성합니다. 반환된 secret 값은 한 번만 노출됩니다.
    https://docs.databricks.com/api/azure/account/serviceprincipalsecrets/create

    Returns:
        {"id": <secret_id>, "secret": "<secret_value>"} 형태. secret_value는 재조회 불가.
    """
    url = f"{DATABRICKS_HOST}/api/2.0/accounts/{DATABRICKS_ACCOUNT_ID}/servicePrincipals/{service_principal_id}/secrets"
    body = {}
    if comment:
        body["comment"] = comment
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json=body,
    )
    response.raise_for_status()
    return response.json()


def delete_service_principal_secret(
    access_token: str, service_principal_id: str, secret_id: int
) -> None:
    """
    Service Principal의 OAuth 시크릿을 삭제합니다.
    https://docs.databricks.com/api/azure/account/serviceprincipalsecrets/delete
    """
    url = f"{DATABRICKS_HOST}/api/2.0/accounts/{DATABRICKS_ACCOUNT_ID}/servicePrincipals/{service_principal_id}/secrets/{secret_id}"
    response = requests.delete(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    response.raise_for_status()


def run_with_temporary_sp_credentials(
    service_principal_id: str,
    run_fn,
    secret_comment: str = "get_network_policy temporary run",
    *,
    bootstrap_token: Optional[str] = None,
    bootstrap_client_id: Optional[str] = None,
    bootstrap_client_secret: Optional[str] = None,
):
    """
    지정한 Service Principal로 OAuth 시크릿을 발급받아 DATABRICKS_CLIENT_ID/SECRET에 설정한 뒤
    run_fn()을 실행하고, 완료 후 발급한 시크릿을 삭제합니다.

    Account API용 부트스트랩은 다음 중 하나:
    - bootstrap_token: 이미 발급된 Bearer 토큰 (예: Azure Managed Identity로 획득)
    - bootstrap_client_id + bootstrap_client_secret: OAuth client credentials로 토큰 발급

    Args:
        service_principal_id: 시크릿 발급·삭제 대상 SP id (숫자 id 또는 application_id)
        run_fn: 인자 없음. 실행 시 전역 DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET 이 이미 설정된 상태.
    """
    global DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET

    if bootstrap_token is None:
        if not bootstrap_client_id or not bootstrap_client_secret:
            raise ValueError(
                "bootstrap_token 또는 (bootstrap_client_id, bootstrap_client_secret) 중 하나를 지정하세요."
            )
        bootstrap_token = get_access_token_with(bootstrap_client_id, bootstrap_client_secret)
        log_debug("Account API 부트스트랩 토큰 획득 완료 (client credentials).")
    else:
        log_debug("Account API 부트스트랩 토큰 사용 (Managed Identity 등).")

    sp_info = get_service_principal(bootstrap_token, service_principal_id)
    app_id = sp_info.get("applicationId") or sp_info.get("application_id") or service_principal_id
    log_info(f"Service Principal 조회 완료: id={service_principal_id}, application_id={app_id}")

    secret_response = create_service_principal_secret(
        bootstrap_token,
        service_principal_id,
        comment=secret_comment,
    )
    secret_id = secret_response["id"]
    client_secret_value = secret_response.get("secret") or secret_response.get("value")
    if not client_secret_value:
        raise ValueError("create_service_principal_secret 응답에 secret/value가 없습니다.")

    # OAuth 토큰 발급에는 Azure AD application_id(UUID) 사용. 전역 설정으로 이후 get_access_token() 등이 사용.
    DATABRICKS_CLIENT_ID = app_id
    DATABRICKS_CLIENT_SECRET = client_secret_value
    log_debug("해당 SP로 Databricks client id/secret 발급 완료. 본 프로세스 실행 후 시크릿 삭제 예정.")

    try:
        run_fn()
    finally:
        try:
            delete_service_principal_secret(bootstrap_token, service_principal_id, secret_id)
            log_info("발급했던 Service Principal 시크릿 삭제 완료.")
        except Exception as e:
            log_info(f"[경고] 시크릿 삭제 실패 (이미 삭제되었거나 권한 부족): {e}")


def get_workspace_network_option(access_token: str, workspace_id: int) -> dict:
    """
    워크스페이스의 네트워크 옵션을 조회합니다.
    
    API: GET /api/2.0/accounts/{account_id}/workspaces/{workspace_id}/network
    
    Args:
        access_token: Databricks 액세스 토큰
        workspace_id: 워크스페이스 ID
        
    Returns:
        네트워크 옵션 딕셔너리
    """
    url = f"{DATABRICKS_HOST}/api/2.0/accounts/{DATABRICKS_ACCOUNT_ID}/workspaces/{workspace_id}/network"
    
    response = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    )
    
    response.raise_for_status()
    return response.json()


def get_network_policy(access_token: str, network_policy_id: str) -> dict:
    """
    네트워크 정책 상세 정보를 조회합니다.
    
    API: GET /api/2.0/accounts/{account_id}/network-policies/{network_policy_id}
    
    Args:
        access_token: Databricks 액세스 토큰
        network_policy_id: 네트워크 정책 ID
        
    Returns:
        네트워크 정책 상세 정보 딕셔너리
    """
    url = f"{DATABRICKS_HOST}/api/2.0/accounts/{DATABRICKS_ACCOUNT_ID}/network-policies/{network_policy_id}"
    
    response = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    )
    
    response.raise_for_status()
    return response.json()


def get_network_policy_details(workspace_id: int) -> dict:
    """
    워크스페이스의 네트워크 정책 상세 정보를 조회합니다.
    
    Args:
        workspace_id: Databricks 워크스페이스 ID
        
    Returns:
        네트워크 정책 상세 정보 딕셔너리
    """
    # 1. 액세스 토큰 획득
    log_debug("[0/2] 액세스 토큰 획득 중...")
    access_token = get_access_token()
    log_debug("      - 토큰 획득 완료")
    
    # 2. 워크스페이스의 네트워크 옵션 조회하여 network_policy_id 획득
    log_debug(f"[1/2] 워크스페이스 {workspace_id}의 네트워크 옵션 조회 중...")
    workspace_network_option = get_workspace_network_option(access_token, workspace_id)
    
    network_policy_id = workspace_network_option.get("network_policy_id")
    log_debug(f"      - Network Policy ID: {network_policy_id}")
    
    # 3. network_policy_id로 네트워크 정책 상세 정보 조회
    log_debug(f"[2/2] 네트워크 정책 '{network_policy_id}' 상세 정보 조회 중...")
    network_policy = get_network_policy(access_token, network_policy_id)
    
    # 결과 구성
    result = {
        "workspace_id": workspace_id,
        "workspace_network_option": workspace_network_option,
        "network_policy": network_policy,
        "network_policy_id": network_policy_id
    }
    
    return result


def compute_hash(data: dict) -> str:
    """
    딕셔너리 데이터의 해시값을 계산합니다.
    
    Args:
        data: 해시할 딕셔너리 데이터
        
    Returns:
        SHA256 해시 문자열
    """
    # JSON 문자열로 변환 (키 정렬하여 일관성 유지)
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()


def table_exists(spark: SparkSession, table_name: str) -> bool:
    """
    테이블 존재 여부를 확인합니다.
    
    Args:
        spark: SparkSession
        table_name: 테이블 이름 (catalog.schema.table)
        
    Returns:
        테이블 존재 여부
    """
    try:
        spark.sql(f"DESCRIBE TABLE {table_name}")
        return True
    except Exception:
        return False


def get_latest_hash(spark: SparkSession, table_name: str, workspace_id: int) -> str:
    """
    테이블에서 해당 워크스페이스의 최신 해시값을 조회합니다.
    
    Args:
        spark: SparkSession
        table_name: 테이블 이름
        workspace_id: 워크스페이스 ID
        
    Returns:
        최신 해시값 (없으면 None)
    """
    try:
        df = spark.sql(f"""
            SELECT policy_hash 
            FROM {table_name} 
            WHERE workspace_id = {workspace_id}
            ORDER BY captured_at DESC 
            LIMIT 1
        """)
        
        if df.count() > 0:
            return df.first()["policy_hash"]
        return None
    except Exception:
        return None


def create_history_table(spark: SparkSession, table_name: str):
    """
    이력 테이블을 생성합니다.
    
    Args:
        spark: SparkSession
        table_name: 테이블 이름 (catalog.schema.table)
    """
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            workspace_id LONG COMMENT '워크스페이스 ID',
            network_policy_id STRING COMMENT '네트워크 정책 ID',
            policy_data STRING COMMENT '전체 정책 데이터 (JSON)',
            policy_hash STRING COMMENT '정책 데이터 해시값 (SHA256)',
            captured_at TIMESTAMP COMMENT '캡처 시간',
            is_current BOOLEAN COMMENT '현재 유효한 레코드 여부'
        )
        USING DELTA
        COMMENT 'Network Policy 변경 이력 테이블 (SCD Type 1)'
    """)
    log_debug(f"테이블 생성 완료: {table_name}")


def save_network_policy_history(
    spark: SparkSession,
    result: dict,
    table_name: str
) -> bool:
    """
    네트워크 정책 정보를 SCD1 패턴으로 Delta 테이블에 저장합니다.
    변경이 있는 경우에만 새 행을 추가합니다.
    
    Args:
        spark: SparkSession
        result: get_network_policy_details() 함수의 반환값
        table_name: 저장할 테이블 이름 (catalog.schema.table)
        
    Returns:
        새 행이 추가되었으면 True, 변경 없으면 False
    """
    workspace_id = result["workspace_id"]
    network_policy = result["network_policy"]
    
    # 현재 데이터의 해시값 계산
    current_hash = compute_hash(result)
    
    # 테이블이 없으면 생성
    if not table_exists(spark, table_name):
        log_debug(f"테이블이 존재하지 않습니다. 새로 생성합니다: {table_name}")
        create_history_table(spark, table_name)
    
    # 최신 해시값 조회
    latest_hash = get_latest_hash(spark, table_name, workspace_id)
    
    # SCD1: 최초 첫 번째(이력 없음)는 무조건 행 입력, 이후는 해시 비교 후 변경 시에만 입력
    if latest_hash is not None and latest_hash == current_hash:
        log_info(f"[변경 없음] 워크스페이스 {workspace_id}의 네트워크 정책에 변경이 없습니다.")
        return False
    
    if latest_hash is None:
        log_info(f"[최초 입력] 워크스페이스 {workspace_id}의 네트워크 정책 이력이 없어 첫 행을 입력합니다.")
    else:
        log_info(f"[변경 감지] 워크스페이스 {workspace_id}의 네트워크 정책이 변경되었습니다.")
    
    # 기존 레코드의 is_current를 False로 업데이트 (SCD1)
    if latest_hash is not None:
        spark.sql(f"""
            UPDATE {table_name}
            SET is_current = FALSE
            WHERE workspace_id = {workspace_id} AND is_current = TRUE
        """)
    
    # 새 레코드 추가
    current_time = datetime.now()
    
    new_row = [(
        workspace_id,
        network_policy.get("network_policy_id"),
        json.dumps(result, ensure_ascii=False),
        current_hash,
        current_time,
        True  # is_current
    )]
    
    schema = StructType([
        StructField("workspace_id", LongType(), False),
        StructField("network_policy_id", StringType(), True),
        StructField("policy_data", StringType(), True),
        StructField("policy_hash", StringType(), False),
        StructField("captured_at", TimestampType(), False),
        StructField("is_current", BooleanType(), False)
    ])
    
    new_df = spark.createDataFrame(new_row, schema)
    new_df.write.mode("append").saveAsTable(table_name)
    
    log_info("[저장 완료] 새 레코드가 추가되었습니다.")
    log_debug(f"  - Policy ID: {network_policy.get('network_policy_id')}")
    log_debug(f"  - Hash: {current_hash[:16]}...")
    log_debug(f"  - Captured At: {current_time}")
    
    return True


def display_network_policy(result: dict):
    """
    네트워크 정책 정보를 보기 좋게 출력합니다. (debug 모드에서만 상세 출력)
    """
    log_debug("\n" + "=" * 60)
    log_debug("네트워크 정책 상세 정보")
    log_debug("=" * 60)
    log_debug(f"Workspace ID: {result['workspace_id']}")
    
    network_policy = result.get('network_policy', {})
    log_debug(f"Network Policy ID: {network_policy.get('network_policy_id')}")
    
    egress = network_policy.get('egress')
    if egress:
        log_debug("\n[Egress 정책]")
        network_access = egress.get('network_access', {})
        
        log_debug(f"  Restriction Mode: {network_access.get('restriction_mode')}")
        
        policy_enforcement = network_access.get('policy_enforcement', {})
        if policy_enforcement:
            log_debug(f"  Enforcement Mode: {policy_enforcement.get('enforcement_mode')}")
            dry_run_products = policy_enforcement.get('dry_run_mode_product_filter', [])
            if dry_run_products:
                log_debug(f"  Dry Run Products: {', '.join(dry_run_products)}")
        
        allowed_internet = network_access.get('allowed_internet_destinations', [])
        if allowed_internet:
            log_debug("\n  [Allowed Internet Destinations]")
            for dest in allowed_internet:
                log_debug(f"    - {dest.get('destination')} ({dest.get('internet_destination_type')})")
        
        allowed_storage = network_access.get('allowed_storage_destinations', [])
        if allowed_storage:
            log_debug("\n  [Allowed Storage Destinations]")
            for dest in allowed_storage:
                log_debug(f"    - Account: {dest.get('azure_storage_account')}")
                log_debug(f"      Service: {dest.get('azure_storage_service')}")
                log_debug(f"      Paths: {dest.get('allowed_paths')}")
    
    log_debug("=" * 60)


# =============================================================================
# 실행
# =============================================================================

def _run_network_policy_collection():
    """네트워크 정책 조회 및 이력 저장 (전역 DATABRICKS_CLIENT_ID/SECRET 사용)."""
    result = get_network_policy_details(WORKSPACE_ID)
    log_info(f"워크스페이스 {result['workspace_id']} 네트워크 정책 조회 완료.")
    display_network_policy(result)
    is_changed = save_network_policy_history(spark, result, TARGET_TABLE)
    if is_changed:
        log_info(f"\n[결과] 새로운 정책 변경 이력이 저장되었습니다: {TARGET_TABLE}")
    else:
        log_info(f"\n[결과] 정책 변경이 없어 이력이 추가되지 않았습니다.")


# Job parameter: debug 모드 설정 (spark.conf job_parameter.debug 또는 환경변수 DEBUG)
_resolve_debug_mode(spark)
if DEBUG_MODE:
    log_info("(debug 모드: 상세 로그 출력)")

# 부트스트랩: Azure Managed Identity 우선, 없으면 DATABRICKS_CLIENT_ID/SECRET(환경변수). 이 SP로 시크릿 발급 → 본 프로세스 실행 → 시크릿 삭제
MI_CLIENT_ID = os.environ.get("MANAGED_IDENTITY_CLIENT_ID") or os.environ.get("AZURE_CLIENT_ID")
bootstrap_token = get_access_token_via_managed_identity(managed_identity_client_id=MI_CLIENT_ID)

if bootstrap_token is not None:
    log_info("Azure Managed Identity로 Account API 토큰 획득. 해당 SP 시크릿 발급 후 본 프로세스 실행.")
    run_with_temporary_sp_credentials(
        service_principal_id=SERVICE_PRINCIPAL_APPLICATION_ID,
        run_fn=_run_network_policy_collection,
        bootstrap_token=bootstrap_token,
    )
elif DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET:
    log_info("환경변수(DATABRICKS_CLIENT_ID/SECRET)로 부트스트랩. 해당 SP 시크릿 발급 후 본 프로세스 실행.")
    run_with_temporary_sp_credentials(
        service_principal_id=SERVICE_PRINCIPAL_APPLICATION_ID,
        run_fn=_run_network_policy_collection,
        bootstrap_client_id=DATABRICKS_CLIENT_ID,
        bootstrap_client_secret=DATABRICKS_CLIENT_SECRET,
    )
else:
    raise ValueError(
        "Account API용 부트스트랩이 필요합니다. "
        "Azure Managed Identity가 연결된 환경에서 실행하거나, "
        "DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET 환경변수를 설정하세요."
    )

