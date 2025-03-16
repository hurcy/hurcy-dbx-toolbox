# Databricks Workspace Deploy using Terraform

이 terraform 은 AWS Customer Managed VPC에 Databricks의 Workspace를 배포합니다.
아래의 Endpoint들을 생성하는 코드를 포함하고 있습니다.
- S3 VPC gateway endpoint
- STS VPC interface endpoint
- Kinesis VPC interface endpoint

### 변수값 설정 

폴더내의 input.tfvars 파일을 배포하려는 Databricks Service Principal의 client_id/client_secret key 접속 정보와 AWS access key/secret key 정보로 수정합니다. 

```
env_name =""
prefix = "" # AWS object prefix
user_name ="" # firstname.lastname
region = "" # AWS Region
deployment_name = "" # Databricks workspace url name. <Account-Prefix>-<deployment_name>.cloud.datarbricks.com
databricks_account_id = "" # databricks account id
client_id="" # client id of a service principal(having admin permission)
client_secret="" # client secret value of the service principal
cidr_block = "10.101.0.0/20" # VPC CIDR 
aws_access_key_id="" # AWS Access Key
aws_secret_access_key="" # AWS Secret Key
```

### 수행 방법 
1. input.tfvars 파일상의 각 정의된 변수값을 수정합니다. 
2. <code>terraform init </code> 을 수행해서 terraform과 provioder를 초기화 합니다. 
3. <code>terraform validate </code> 를 수행해서 코드상의 오류가 없는지 검증합니다.
4. <code>terraform plan -var-file=input.tfvars</code> 를 수행해서 resource를 배포전에 플랜을 확인 합니다.
5. <code>terraform apply -var-file=input.tfvars</code> 를 수행해서 resource를 배포합니다. 
6. <code>terraform destroy -var-file=input.tfvars</code> 를 수행해서 resource를 삭제합니다. 
