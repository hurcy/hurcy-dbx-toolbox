#!/bin/bash

# 인증서 파일 경로 지정 (Workspace 파일 또는 Unity Catalog 볼륨에 저장된 파일 경로)
CERT_FILE="/Volumes/main/default/scripts/scm-ca.crt"
# 또는 Unity Catalog 볼륨 사용 시: CERT_FILE="/Volumes/catalogs/schemas/volumes/path/to/myca.crt"

# 인증서 파일 내용을 시스템 인증서 디렉토리에 복사
if [ -f "$CERT_FILE" ]; then
  echo "Certificate file found, installing..."
  cp "$CERT_FILE" /usr/local/share/ca-certificates/myca.crt
  
  # 시스템 인증서 업데이트
  update-ca-certificates
  
  # Java 키스토어에도 인증서 추가
  PEM_FILE="/etc/ssl/certs/myca.pem"
  PASSWORD="changeit"
  JAVA_HOME=$(readlink -f /usr/bin/java | sed "s:bin/java::")
  KEYSTORE="$JAVA_HOME/lib/security/cacerts"
  
  # 여러 인증서가 PEM 파일에 있는 경우 처리
  CERTS=$(grep 'END CERTIFICATE' $PEM_FILE | wc -l)
  
  # 각 인증서를 PEM 파일에서 추출하여 Java 키스토어에 가져오기
  for N in $(seq 0 $(($CERTS - 1))); do
    ALIAS="myca$N"
    
    cat $PEM_FILE |
      awk "n==$N { print }; /BEGIN CERTIFICATE/ { n++ }" |
      openssl x509 -outform DER |
      keytool -importcert -keystore $KEYSTORE -storepass $PASSWORD -alias $ALIAS -noprompt
  done
  
  # Python requests 라이브러리를 위한 환경 변수 설정
  echo "export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt" >> /databricks/spark/conf/spark-env.sh
  echo "Certificate installation completed successfully"
  export GIT_PROXY_CA_CERT_PATH=/etc/ssl/certs/ca-certificates.crt
  #export GIT_PROXY_TEST_URL=https://please.change.me.com
  export GIT_PROXY_ENABLE_SSL_VERIFICATION=true
else
  echo "ERROR: Certificate file not found at $CERT_FILE"
  exit 1
fi
