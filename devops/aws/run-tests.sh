# RAFS tests currently require the data ingestion pipeline on the environment
# Most of our envs don't have this data ingested, so we skip the tests for now
# This avoid a false negative, failing the entire pipeline stage because of it
if [ -z "${RUN_RAFS_DDMS_TESTS}" ]; then
  echo "RAFS Tests Skipped, RUN_RAFS_DDMS_TESTS env var not set"
  exit 0;
fi



wget -O /usr/local/bin/jq https://github.com/stedolan/jq/releases/download/jq-1.6/jq-linux64
chmod +x /usr/local/bin/jq

export ACCESS_TOKEN=$(curl --location --request POST "https://cognito-idp.${AWS_REGION}.amazonaws.com/" \
     --header 'X-Amz-Target: AWSCognitoIdentityProviderService.InitiateAuth' \
     --header 'Content-Type: application/x-amz-json-1.1' \
     --data-raw "{ \
         \"AuthFlow\": \"${AWS_COGNITO_AUTH_FLOW}\", \
         \"AuthParameters\": { \
             \"PASSWORD\": \"${ADMIN_PASSWORD}\", \
             \"USERNAME\": \"${ADMIN_USER}\" \
         }, \
         \"ClientId\": \"${AWS_COGNITO_CLIENT_ID}\" \
	     }" | jq '.AuthenticationResult.AccessToken')

# Set variables
BUILD_DIR=artifacts/os-rafs-ddms-services
TEST_DIR=$BUILD_DIR/testing/integration/build-aws
PARTITION=opendes
URL_PREFIX=api/rafs-ddms
CLOUD_PROVIDER=aws
DDMS_BASE_URL=$HOST

# Parse container image from build-info.json
TEST_IMAGE=$(jq -r .artifacts[1] $BUILD_DIR/build-info.json)
echo Running with image $TEST_IMAGE

# Create env file
cat > .env <<EOF
SERVICE_NAME=rafs-ddms
OPENAPI_PREFIX=/api/rafs-ddms
CLOUD_PROVIDER=aws
SERVICE_HOST_STORAGE=$DDMS_BASE_URL/api/storage/v2
SERVICE_HOST_SEARCH=$DDMS_BASE_URL/api/search/v2
SERVICE_HOST_PARTITION=$DDMS_BASE_URL/api/partition/v1
SERVICE_HOST_DATASET=$DDMS_BASE_URL/api/dataset/v1
SERVICE_HOST_LEGAL=$DDMS_BASE_URL/api/legal/v1
SERVICE_HOST_SCHEMA=$DDMS_BASE_URL/api/schema-service/v1
CACHE_ENABLE=False
URL_PREFIX=api/rafs-ddms
PARTITION=opendes
EOF

# Log in to ECR
ECR_REPO=$(cut -d '/' -f 1 <<< "$TEST_IMAGE")
ECR_REGION=$(cut -d '.' -f 4 <<< "$ECR_REPO")
aws ecr get-login-password --region $ECR_REGION | docker login --username AWS --password-stdin $ECR_REPO

# Run integration tests
echo "ls test dir"
ls $(pwd)/$TEST_DIR/tests/
docker run \
    --env-file .env \
    -v $(pwd)/$TEST_DIR/tests/:/tests \
    -v $(pwd)/$TEST_DIR/client/:/client \
    -w / \
    $TEST_IMAGE bash -c "pytest -n auto --cov=app --cov-report=term ./tests/integration/tests --ddms-base-url $DDMS_BASE_URL --url-prefix $URL_PREFIX --partition $PARTITION --bearer-token $ACCESS_TOKEN --cloud-provider $CLOUD_PROVIDER"
