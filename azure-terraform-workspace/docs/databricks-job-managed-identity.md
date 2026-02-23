# Databricks Job with Azure Managed Identity 구성

`get_network_policy.py`에서 Azure Managed Identity로 Account API 토큰을 쓰려면 아래 두 가지 방식 중 하나로 구성할 수 있습니다.

---

## 본 문서 방식 vs 계정 전체 토큰 페더레이션 (Microsoft)

[페더레이션 정책 구성 - Azure Databricks](https://learn.microsoft.com/ko-kr/azure/databricks/dev-tools/auth/oauth-federation-policy)의 **계정 전체 토큰 페더레이션**과 이 문서의 방식은 **토큰 방향**과 **목적**이 다릅니다.

| 구분 | 본 문서 (WIF / VM+MI) | 계정 전체 토큰 페더레이션 |
|------|------------------------|---------------------------|
| **목적** | Databricks Job(또는 VM)에서 **Azure AD 토큰을 어떻게 얻을지** | **외부 IdP가 발급한 토큰**으로 Databricks API에 로그인하도록 허용 |
| **토큰 방향** | **Azure AD가 발급한 토큰** → Databricks Account API 호출 시 Bearer로 사용 | **조직 IdP(또는 GitHub 등)가 발급한 토큰** → Databricks가 검증 후 사용자/SP로 매핑 |
| **설정 주체** | Azure(Managed Identity, Entra Federated credential) + Databricks(SP 등록, 클러스터 권한) | **Databricks 계정 관리자**만: 계정 페더레이션 정책(발급자 URL, 관객, 주체 클레임) 등록 |
| **설정 위치** | Entra ID: “Databricks를 발급자로 하는 토큰을 이 MI의 federated credential로 허용” | Databricks: “이 발급자(issuer)의 토큰을 신뢰하고, 주체(subject)로 사용자/SP 매핑” |
| **비밀 관리** | Azure MI 사용 시 Databricks 쪽 장기 비밀 불필요. (WIF는 토큰 파일, VM은 IMDS) | Databricks 비밀 없이 **IdP 토큰만**으로 Databricks API 호출 가능 |
| **적용 범위** | 특정 Job/클러스터 또는 VM(어디서 Azure 토큰을 가져올지) | **계정 전체**: 해당 정책에 맞는 IdP 토큰을 쓰는 모든 호출 |

**요약**

- **본 문서**: “Account API를 부르려면 Bearer 토큰이 필요한데, 그 토큰을 **Azure AD에서** 어떻게 받을지”(Managed Identity + WIF 또는 VM+IMDS).
- **계정 전체 토큰 페더레이션**: “**우리 회사 IdP(또는 GitHub 등)가 준 토큰**을 Databricks가 사용자/서비스 주체로 인식하게 하는 정책”.  
  즉, **외부 IdP → Databricks** 방향이며, Databricks가 그 IdP를 신뢰하도록 설정하는 것입니다.

같은 Microsoft 문서의 **서비스 주체 페더레이션 정책**은 “특정 서비스 주체”에 대해 “이 issuer/audience/subject를 가진 토큰이 이 SP로 로그인 가능”하게 하는 것이며, 역시 **외부 토큰 → Databricks** 구조입니다.  
본 문서의 WIF는 **Databricks가 발급한 토큰 → Azure가 수락 → Azure AD 토큰 발급**이므로, 방향이 반대입니다.

---

## 전제: SP가 account admin, account admin 필요 REST API 호출용 토큰

**가정**: 서비스 주체(SP)에 account admin 권한이 부여되어 있고, 이 SP의 권한으로 **account admin이 필요한 REST API**(예: Account API의 SP 조회, 시크릿 생성/삭제, 네트워크 정책 조회 등)를 호출하기 위한 **토큰 발급 방식**만 비교한다.

### 방식 A: 본 문서 (Azure AD 토큰으로 SP 대신 호출)

- **토큰 성격**: **Azure AD(Entra ID)가 발급한 토큰**이다. 토큰의 주체(subject)는 해당 SP(또는 SP와 연결된 Managed Identity)이다.  
  즉, “이 SP다”라고 증명하는 토큰을 **Azure AD가 발급**하고, 그 토큰을 Bearer로 넣어 Databricks Account API를 호출한다.
- **발급 경로** (택일):
  1. **Client credentials**: SP의 `client_id` + `client_secret`으로 Azure AD에 요청 → 액세스 토큰 발급. (비밀 관리 필요.)
  2. **VM + Managed Identity**: SP와 연결된 UAMI를 VM에 할당 → VM에서 IMDS로 Azure AD 토큰 발급. (비밀 없음, VM에서만 가능.)
  3. **Databricks Job + WIF**: 워크스페이스에 할당된 UAMI에 Entra Federated credential 설정(Databricks OIDC 발급자 신뢰) → Job에서 Databricks가 마운트한 토큰 파일로 Azure AD에 증명 → Azure AD가 해당 UAMI용 토큰 발급. (비밀 없음, Shared/UC 클러스터에서 IMDS 대신 사용.)
- **Account API 호출**: 위에서 받은 **Azure AD Bearer 토큰**을 `Authorization: Bearer <token>`으로 보낸다. Databricks는 Azure AD가 서명한 토큰을 검증하고, 그 토큰의 주체에 해당하는 Databricks SP(account admin)로 요청을 처리한다.
- **정리**: “account admin SP **본인**의 Azure AD 토큰”을 받아서 쓰는 방식이다. SP 계정이 account admin이면, 이 토큰으로 account admin 필요 API를 호출할 수 있다.

### 방식 B: 서비스 주체 페더레이션 정책 (외부 IdP 토큰으로 SP 대신 호출)

- **토큰 성격**: **외부 IdP**(GitHub Actions, 회사 OIDC, Azure DevOps 등)가 발급한 **JWT**이다.  
  이 토큰은 “해당 SP의 client_id/secret이 아니다”. 대신 Databricks **서비스 주체 페더레이션 정책**에서 “이 issuer/audience/subject를 가진 토큰은 **이 SP로 로그인한 것**으로 간주한다”고 설정해 둔 것이다.
- **설정**: account admin 권한을 가진 **그 SP**에 대해, 계정 콘솔에서 **서비스 주체 페더레이션 정책**을 만든다.  
  발급자(issuer), 관객(audiences), 주체(subject)를 지정하고, (선택) JWKS로 서명 검증을 설정한다.  
  예: GitHub Actions라면 issuer=`https://token.actions.githubusercontent.com`, subject=`repo:org/repo:environment:prod` 등.
- **토큰 발급**: 워크로드는 **Azure AD가 아니라** 해당 IdP(GitHub, 회사 IdP 등)에서 JWT를 받는다. (예: GitHub OIDC 토큰, 회사 IdP의 client_credentials 토큰.)
- **Account API 호출**: 그 **외부 IdP JWT**를 Bearer로 Databricks Account API에 보낸다. Databricks는 계정에 등록된 **서비스 주체 페더레이션 정책**으로 검증하고, 정책에 맞으면 “이 요청은 해당 SP(account admin)가 한 요청”으로 처리한다.  
  즉, “SP 본인의 Azure AD 토큰”이 아니라 “**다른 IdP 토큰**을 그 SP로 매핑해서” 쓰는 방식이다.
- **정리**: “account admin SP **본인**의 비밀/토큰”을 쓰지 않고, **외부 IdP 토큰**만으로 그 SP 권한으로 API를 호출할 수 있다. SP의 client_id/secret 또는 Azure MI를 Databricks Job/VM에 둘 필요가 없다.

### 비교 요약 (SP = account admin, account admin 필요 API용 토큰)

| 항목 | 방식 A (본 문서: Azure AD 토큰) | 방식 B (서비스 주체 페더레이션 정책) |
|------|----------------------------------|--------------------------------------|
| **호출 시 사용하는 토큰** | Azure AD가 발급한, 해당 SP(또는 연결된 MI)용 토큰 | 외부 IdP가 발급한 JWT (GitHub, 회사 OIDC 등) |
| **SP 비밀/자격 증명** | client_id/secret 사용 경로는 비밀 관리 필요. MI/WIF 경로는 비밀 없이 토큰만 발급. | SP의 client_id/secret 또는 Azure MI 불필요 (IdP 쪽만 구성) |
| **토큰 발급처** | Azure AD (client credentials / MI / WIF) | 외부 IdP (GitHub, Azure DevOps, 회사 IdP 등) |
| **Databricks 측 설정** | SP를 Account에 등록 + (WIF 시) 워크스페이스/클러스터 권한 | **같은 SP**에 **서비스 주체 페더레이션 정책** 추가 (issuer/audience/subject) |
| **실행 환경** | VM(IMDS), Databricks Job(WIF 또는 client credentials) 등 | IdP 토큰을 얻을 수 있는 어디서든 (GitHub Actions, CI, 온프레미스 등) |
| **적합한 경우** | 이미 Azure AD SP 또는 MI로 통일하고 싶을 때, Databricks Job/VM에서 Azure 토큰만 쓰고 싶을 때 | GitHub Actions·CI·회사 IdP 등 **비-Azure** 또는 **IdP 통일**이 중요할 때 |

둘 다 “account admin SP 권한으로 account admin 필요 API를 호출하기 위한 토큰”을 다루지만,  
- **방식 A**는 “그 SP(또는 연결된 MI) **본인의 Azure AD 토큰**을 어떻게 발급받을지”에 초점을 두고,  
- **방식 B**는 “**다른 IdP 토큰**을 Databricks가 그 SP로 인식하게 하는 정책”에 초점을 둔다.

### Keyless(비밀/키 미사용) 인증이 필요할 때

**Keyless** = 장기 비밀(client_secret, API key 등)을 저장·회전하지 않고, 단기 토큰 또는 페더레이션만으로 인증하는 방식.

| 요구 사항 | 적합한 방법 | 이유 |
|-----------|-------------|------|
| **Keyless + 실행 위치가 Azure(Databricks Job 또는 VM)** | **방식 A 중 MI 또는 WIF** | VM+MI: IMDS로 토큰 발급(비밀 없음). Job+WIF: Databricks가 마운트한 토큰 파일로 Azure AD 토큰 발급(비밀 없음). SP의 client_secret을 둘 필요가 없다. |
| **Keyless + 실행 위치가 GitHub Actions / CI / 비-Azure** | **방식 B (서비스 주체 페더레이션 정책)** | GitHub OIDC 등 IdP가 단기 JWT를 발급하고, Databricks가 그 토큰을 SP로 매핑. SP 비밀·Azure MI를 어디에도 저장하지 않아도 된다. |
| **Keyless + 실행 위치 제한 없이 통일하고 싶음** | **방식 B** | IdP만 OIDC/페더레이션을 지원하면 어디서든 동일한 방식(IdP 토큰 → Databricks)으로 keyless 가능. |

**정리**

- **Azure 안에서만** 돌리고 keyless로 가려면 → **방식 A의 MI 또는 WIF**가 적합하다. (방식 A의 client credentials 경로는 client_secret이 필요하므로 keyless가 아니다.)
- **GitHub Actions, 다른 CI, 온프레미스** 등 **비-Azure 또는 여러 환경**에서 keyless로 통일하려면 → **방식 B(서비스 주체 페더레이션 정책)**가 적합하다. SP 비밀을 전혀 두지 않고, IdP가 발급한 단기 토큰만으로 account admin API를 호출할 수 있다.

---

## 제한 사항 (Unity Catalog / Shared 모드)

- **IMDS 미지원**: Databricks 클러스터(특히 Unity Catalog **Shared** access mode)에서는 Azure Instance Metadata Service(IMDS)에 접근할 수 **없습니다**.
- 따라서 `ManagedIdentityCredential`만 쓰면 "no response from the IMDS endpoint" 오류가 납니다.
- **권장**: Workload Identity Federation(WIF) 또는 **Azure VM + MI** 방식 사용.

---

## 방식 1: Workload Identity Federation (WIF) – Databricks Job에서 MI 사용

Job이 **Databricks Shared(Unity Catalog) 클러스터**에서 돌 때, **워크스페이스에 연결된 User-Assigned MI**를 WIF로 사용하는 방법입니다.

### 1. Azure 측

1. **User-Assigned Managed Identity(UAMI) 생성**  
   Azure Portal → Managed identities → Create → 이름/리소스 그룹 지정 후 생성.  
   **개요**에서 **Client ID** 복사.

2. **워크스페이스에 UAMI 할당**  
   Azure Portal → 해당 Databricks 워크스페이스 → **Identity** → User assigned → Add → 방금 만든 UAMI 선택.

3. **Federated credential 등록 (Entra ID)**  
   UAMI는 **App registrations**에는 없고, **Enterprise applications**에서만 보입니다. 검색이 안 되면 아래를 사용하세요.
   - **경로 A (권장)**  
     Azure Portal → **Managed identities** → 방금 만든 UAMI 리소스 클릭 → 왼쪽 메뉴에서 **Federated credentials** (또는 **Federated credential**).  
     여기서 **Add credential**으로 발급자/Subject/Audience 입력. (리소스 블레이드에서 바로 설정 가능한 경우.)
   - **경로 B (Enterprise applications)**  
     Microsoft Entra ID → **Enterprise applications** → 상단 검색창에 UAMI의 **Client ID**(GUID)를 **그대로 붙여넣기** 후 검색.  
     이름으로는 안 나올 수 있으므로 반드시 **Client ID**로 검색.  
     또는 **Application type** 필터에서 **Managed identity** 선택 후 목록에서 해당 UAMI 선택.  
     들어가면 **Certificates & secrets** 옆 **Federated credentials** → **Add credential**.
   - **공통 설정값**  
     - **Federated credential scenario**: "Issuer-based (e.g. OIDC)" 또는 **"Other"**.  
     - **Issuer**: Account OIDC 사용 시 `https://accounts.azuredatabricks.net/oidc/accounts/<account-id>`. (예: `https://accounts.azuredatabricks.net/oidc/accounts/ccb842e7-2376-4152-b0b0-29fa952379b8`)  
     - **Subject identifier**: Databricks에서 이 토큰을 발급할 주체. Account 수준이면 SP(서비스 주체)의 **Application ID**(GUID)를 넣는 경우가 있음. (예: `9a77e2bc-49f4-45c7-b4bb-1f61f9f956bd`)  
     - **Audience**: `api://AzureADTokenExchange`.  
     - **Name**: 식별용 이름(예: `databricks_account_admin_sp`).

4. **UAMI에 Databricks Account 권한 부여**  
   Account 레벨에서 해당 MI를 서비스 프린시펄로 추가하고, SP 조회/시크릿 생성·삭제 등 필요한 역할(예: Account admin) 부여.

### 2. Databricks 측

1. **UAMI를 워크스페이스 Service Principal로 등록**  
   Databricks → **Admin Console** → **Service principals** → Add Service Principal → UAMI의 **Client ID**를 Application ID로 입력.

2. **Job용 컴퓨트에 SP 권한 부여**  
   **Compute** → Job에서 사용하는 클러스터(또는 Job cluster) → **Permissions** → Add → 방금 등록한 SP 선택 → 최소 **Can Attach To** 부여.

3. **Shared(Unity Catalog) + WIF 지원 클러스터 사용**  
   - Access mode: **Shared (Unity Catalog)**.
   - Databricks Runtime 13.3+ 등 WIF 지원 버전 사용.
   - 재시작 후 노트북에서 `/var/run/secrets/tokens/azure-identity-token` 존재 여부 확인:
     ```python
     import os
     print(os.path.exists("/var/run/secrets/tokens/azure-identity-token"))  # True 여야 함
     ```

### 3. Job/노트북에서 환경 변수 설정

Job task(노트북 또는 스크립트) **맨 앞**에서 다음을 설정한 뒤 `get_network_policy.py` 실행:

```python
import os
os.environ["AZURE_CLIENT_ID"] = "<UAMI-client-id>"
os.environ["AZURE_TENANT_ID"] = "<tenant-id>"
os.environ["AZURE_FEDERATED_TOKEN_FILE"] = "/var/run/secrets/tokens/azure-identity-token"
```

- `get_network_policy.py`는 **WIF**를 지원합니다. `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_FEDERATED_TOKEN_FILE` 세 개가 모두 설정되면 **WIF만** 시도하고(IMDS로 fallback하지 않음), 토큰 파일이 없으면 안내 메시지 후 실패합니다. 세 변수 중 하나라도 없으면 VM용 **ManagedIdentityCredential**(IMDS)만 시도합니다.

### 4. 트러블슈팅: Databricks Job에서 "IMDS endpoint" / "ManagedIdentityCredential" 오류

다음과 비슷한 메시지가 나오면 **WIF 경로가 아니라 IMDS(ManagedIdentityCredential)**가 호출된 상태입니다.

```
ImdsCredential.get_token failed: ManagedIdentityCredential authentication unavailable, no response from the IMDS endpoint.
ManagedIdentityCredential.get_token failed: ...
```

**원인**  
- Job/노트북에서 `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_FEDERATED_TOKEN_FILE` 세 환경 변수가 **설정되지 않았거나**,  
- `AZURE_FEDERATED_TOKEN_FILE`에 지정한 경로에 **파일이 없음** (클러스터에 WIF 토큰이 마운트되지 않음).

**조치**  
1. 노트북/Job **맨 앞 셀**에서 위 세 환경 변수를 반드시 설정한 뒤 스크립트 실행.  
2. 토큰 파일 존재 확인: `print(os.path.isfile(os.environ.get("AZURE_FEDERATED_TOKEN_FILE", ""))))` → `True`여야 함.  
3. `False`이면: 클러스터가 **Shared (Unity Catalog)** 인지, UAMI를 **Service Principal**로 등록했는지, 해당 SP에 이 클러스터에 대한 **Can Attach To** 권한을 줬는지 확인.  
4. 코드 수정 후에는 WIF env가 설정된 경우 **IMDS로 fallback하지 않으므로**, 토큰 파일이 없으면 "토큰 파일이 없습니다" 안내만 나오고 IMDS 오류는 나오지 않습니다.

### 5. AZURE_FEDERATED_TOKEN_FILE 경로에 토큰 파일이 생기게 하려면

`/var/run/secrets/tokens/azure-identity-token` 파일은 **Databricks가 클러스터를 해당 서비스 주체(SP) 컨텍스트로 실행할 때** 마운트합니다. 아래를 **순서대로** 모두 만족해야 합니다.

#### 5.1 워크스페이스에서 Identity Federation 활성화

- **워크스페이스 설정**에서 **Workload Identity Federation** (또는 **Identity Federation**)이 켜져 있어야 합니다.
- 일부 리전·플랜에서만 지원되므로, 사용 중인 Azure Databricks 제품/리전에서 지원 여부를 확인하세요.
- 참고: [Authenticate with an identity provider token](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/auth/oauth-federation-exchange)

#### 5.2 UAMI를 Databricks Service Principal로 등록

- Databricks **Admin Console** (워크스페이스 설정) → **Service principals** → **Add Service Principal**.
- **Application ID**에 UAMI의 **Client ID**(GUID) 입력 후 저장.

#### 5.3 Shared(Unity Catalog) 클러스터 사용

- Job에서 쓰는 **클러스터**(또는 Job cluster)를 다음으로 설정:
  - **Access mode**: **Shared (Unity Catalog)**.  
    (Single user / No isolation shared는 토큰 파일이 마운트되지 않을 수 있음.)
  - **Databricks Runtime**: 13.3 LTS 이상 등 WIF를 지원하는 버전.

#### 5.4 해당 클러스터에 SP 권한 부여

- **Compute** → 해당 클러스터 → **Permissions** (또는 ⋮ → Permissions).
- **Add permissions** → 방금 등록한 **Service principal**(UAMI) 선택.
- 최소 **Can Attach To** 부여 후 저장.
- **클러스터 재시작** (중요: 권한 변경 후 재시작해야 토큰 마운트가 적용될 수 있음).

#### 5.5 Job이 그 SP로 실행되도록 설정

- 토큰 파일은 **클러스터가 그 서비스 주체의 identity로 attach/실행될 때** 마운트됩니다.
- **Workflows** → 해당 **Job** → **Settings** (또는 **Configure**).
- **Run as** (또는 **Job identity** / **실행 identity**)를 **해당 Service principal**(UAMI로 등록한 SP)로 설정.
- Job 소유권을 그 SP로 이전했거나, task가 그 SP identity로 돌도록 설정되어 있어야 합니다.  
  참고: [Run a job with a Microsoft Entra ID service principal](https://learn.microsoft.com/en-us/azure/databricks/jobs/how-to/run-jobs-with-service-principals)

#### 5.6 동작 확인

- Job을 한 번 실행한 뒤, 노트북/스크립트 **맨 앞**에서 다음으로 파일 존재 여부 확인:
  ```python
  import os
  path = "/var/run/secrets/tokens/azure-identity-token"
  print("Token file exists:", os.path.isfile(path))
  ```
- `True`가 나와야 WIF 경로 사용 가능. `False`이면 위 5.1~5.5를 다시 확인하고, 지원 리전/플랜·공식 문서를 확인하세요.

---

### 6. 트러블슈팅: "[WIF] 토큰 파일이 없습니다"

이 메시지는 `AZURE_FEDERATED_TOKEN_FILE`에 지정한 경로에 파일이 없다는 뜻입니다. **위 §5 (토큰 파일이 생기게 하려면)** 를 순서대로 적용했는지 확인하세요. 특히 **Job Run as = 해당 SP**인지, **Shared(UC) 클러스터**에 **Can Attach To** 후 **재시작**했는지가 중요합니다.

**당장 WIF 없이 실행하려면 (대안)**  
- 부트스트랩에 **client credentials**를 쓰려면: **AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_FEDERATED_TOKEN_FILE 세 개를 설정하지 말고**,  
  **DATABRICKS_CLIENT_ID**, **DATABRICKS_CLIENT_SECRET**만 설정하세요.  
  그러면 코드는 WIF를 시도하지 않고 client credentials 경로로 부트스트랩합니다. (Account admin 권한이 있는 SP의 client_id/secret을 Databricks 시크릿 등에 넣어 두고 Job에서 주입하면 됩니다.)

### 7. 참고

- Issuer/Subject 형식은 Databricks 버전·리전에 따라 다를 수 있으므로, 공식 문서([Authenticate with Azure managed identities](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/auth/azure-mi), [Workload Identity Federation](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/auth/oauth-federation-exchange))를 반드시 확인하세요.
- `/var/run/secrets/tokens/azure-identity-token`이 존재하지 않으면 WIF가 해당 클러스터에 적용되지 않은 것이므로, SP 등록·클러스터 권한·Access mode를 다시 확인해야 합니다.

---

## 방식 2: Azure VM + MI (Databricks CLI/API 호출)

Job을 **Databricks 안**에서 돌리지 않고, **Azure VM**에서 스크립트가 MI로 토큰을 받아 Account API를 호출하는 방식입니다.

### 1. Azure 측

1. **User-Assigned Managed Identity(UAMI) 생성** (방식 1과 동일).
2. **UAMI를 Databricks Account에 서비스 프린시펄로 추가**  
   Account 콘솔에서 **Microsoft Entra ID managed**로 UAMI의 Client ID 추가.
3. **UAMI를 워크스페이스에도 할당** (필요 시).
4. **Azure VM 생성** (Ubuntu 등).
5. **VM에 UAMI 할당**  
   VM → **Identity** → User assigned → Add → UAMI 선택.

### 2. VM에서 인증 설정

VM에 SSH 접속 후 Databricks CLI 설치 및 설정:

```bash
# CLI 설치 (예시)
sudo apt install unzip
curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sudo sh
```

`~/.databrickscfg` 예시 (Account API 사용 시):

```ini
[AZURE_MI_ACCOUNT]
host = https://accounts.azuredatabricks.net
account_id = <account-id>
azure_client_id = <UAMI-client-id>
azure_use_msi = true
```

### 3. Python에서 MI 토큰 사용

VM에서 실행하는 Python 스크립트는 **IMDS**를 사용할 수 있으므로, `get_network_policy.py`의 `ManagedIdentityCredential` 경로가 그대로 동작합니다.  
환경 변수로 UAMI 지정 시:

```bash
export MANAGED_IDENTITY_CLIENT_ID="<UAMI-client-id>"
# 또는
export AZURE_CLIENT_ID="<UAMI-client-id>"
```

그 후 스크립트 실행. (같은 VM에서 Databricks API를 호출하거나, 필요 시 Job을 트리거하도록 구성할 수 있음.)

---

## 요약

| 실행 위치              | IMDS 사용 가능? | 권장 방식                                      |
|-----------------------|----------------|-----------------------------------------------|
| Databricks Job (Shared/UC) | 아니오          | Workload Identity Federation + DefaultAzureCredential |
| Azure VM              | 예             | ManagedIdentityCredential (현재 스크립트 지원) |

- **Databricks Job with MI**를 쓰려면: **WIF**를 켜고, UAMI를 워크스페이스·Account에 등록한 뒤, 클러스터에 토큰 파일이 마운트되도록 하고, 노트북/스크립트에서 `AZURE_*` 환경 변수와 `DefaultAzureCredential`(또는 WIF 전용 credential)을 사용하면 됩니다.
- **Azure VM에서만** 실행한다면: VM에 UAMI를 붙이고, 현재처럼 `ManagedIdentityCredential` + (선택) `MANAGED_IDENTITY_CLIENT_ID`만으로 구성하면 됩니다.
