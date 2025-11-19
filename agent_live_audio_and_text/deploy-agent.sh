#!/bin/bash

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_ID="formare-ai"
REGION="europe-west4"
AGENT_SERVICE_NAME="factory-ai-agent-backend-live"
MCP_SERVICE_NAME="factory-ai-agent-mcp-server"
AGENT_SERVICE_ACCOUNT="factory-ai-agent-sa"

echo -e "${BLUE}╔═══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   ADK Factory AI Agent Deployment     ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════╝${NC}"
echo ""


# Get MCP server URL
echo -e "${BLUE}[2/6]${NC} Getting MCP server URL..."

# Temporarily disable exit on error for this command
set +e
MCP_SERVER_OUTPUT=$(gcloud run services describe ${MCP_SERVICE_NAME} \
    --region=${REGION} \
    --format='value(status.url)' 2>&1)
GCLOUD_EXIT_CODE=$?
set -e

if [ $GCLOUD_EXIT_CODE -ne 0 ]; then
    echo -e "${RED}✗${NC} Failed to get MCP server URL"
    echo -e "${YELLOW}Error:${NC}"
    echo "$MCP_SERVER_OUTPUT"
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo "  1. Check if MCP server is deployed:"
    echo "     gcloud run services list --region=${REGION}"
    echo "  2. Verify service name: ${MCP_SERVICE_NAME}"
    echo "  3. Verify region: ${REGION}"
    echo "  4. Check your GCP project: ${PROJECT_ID}"
    exit 1
fi

if [ -z "$MCP_SERVER_OUTPUT" ]; then
    echo -e "${RED}✗${NC} MCP server not found or returned empty URL!"
    echo -e "${YELLOW}Please deploy the MCP server first${NC}"
    echo ""
    echo "Available services:"
    gcloud run services list --region=${REGION} --project=${PROJECT_ID}
    exit 1
fi

MCP_SERVER_URL="${MCP_SERVER_OUTPUT}/sse"
echo -e "${GREEN}✓${NC} MCP: ${MCP_SERVER_URL}"

# Setup service account
echo -e "${BLUE}[3/6]${NC} Setting up service account..."

set +e
gcloud iam service-accounts create ${AGENT_SERVICE_ACCOUNT} \
    --display-name="Pandas ADK Agent" \
    --project=${PROJECT_ID} 2>/dev/null
SA_CREATE_EXIT=$?
set -e

if [ $SA_CREATE_EXIT -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Service account created"
else
    echo -e "${YELLOW}ℹ${NC} Service account already exists"
fi

# Grant Vertex AI access
echo -e "${BLUE}   ${NC} Granting Vertex AI access..."
set +e
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${AGENT_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user" \
    --quiet 2>&1 | grep -v "already exists" || true
set -e

# Grant MCP server access
echo -e "${BLUE}   ${NC} Granting MCP server access..."
set +e
gcloud run services add-iam-policy-binding ${MCP_SERVICE_NAME} \
    --region=${REGION} \
    --member="serviceAccount:${AGENT_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/run.invoker" \
    --quiet 2>&1 | grep -v "already exists" || true
set -e

echo -e "${GREEN}✓${NC} Service account configured"

# Deploy
echo -e "${BLUE}[4/6]${NC} Deploying to Cloud Run..."
echo -e "${YELLOW}⏳${NC} This takes 2-4 minutes..."

set +e
DEPLOY_OUTPUT=$(gcloud run deploy ${AGENT_SERVICE_NAME} \
    --source . \
    --region=europe-west1 \
    --platform=managed \
    --no-allow-unauthenticated \
    --service-account=${AGENT_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com \
    --set-env-vars "MCP_SERVER_URL=${MCP_SERVER_URL},MODEL=gemini-2.5-flash,GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION}" \
    --memory=16Gi \
    --cpu=8 \
    --gpu=1 \
    --gpu-type=nvidia-l4 \
    --no-gpu-zonal-redundancy \
    --timeout=300s \
    --concurrency=80 \
    --min-instances=1 \
    --max-instances=3 \
    --no-cpu-throttling \
    --cpu-boost \
    --project=${PROJECT_ID} \
    --quiet 2>&1)
DEPLOY_EXIT=$?
set -e

if [ $DEPLOY_EXIT -ne 0 ]; then
    echo -e "${RED}✗${NC} Deployment failed!"
    echo -e "${YELLOW}Error:${NC}"
    echo "$DEPLOY_OUTPUT"
    exit 1
fi

echo -e "${GREEN}✓${NC} Deployed!"

# Get URL
echo -e "${BLUE}[5/6]${NC} Getting URL..."

set +e
AGENT_URL=$(gcloud run services describe ${AGENT_SERVICE_NAME} \
    --region=${REGION} \
    --format='value(status.url)' \
    --project=${PROJECT_ID} 2>&1)
URL_EXIT=$?
set -e

if [ $URL_EXIT -ne 0 ] || [ -z "$AGENT_URL" ]; then
    echo -e "${RED}✗${NC} Failed to get service URL"
    echo "$AGENT_URL"
    exit 1
fi

echo -e "${GREEN}✓${NC} URL: ${AGENT_URL}"

# Configure access
echo ""
echo -e "${BLUE}[6/6]${NC} Configure access..."
read -p "Enable public access? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    set +e
    PUBLIC_ACCESS_OUTPUT=$(gcloud run services add-iam-policy-binding ${AGENT_SERVICE_NAME} \
        --region=${REGION} \
        --member="allUsers" \
        --role="roles/run.invoker" \
        --project=${PROJECT_ID} \
        --quiet 2>&1)
    PUBLIC_EXIT=$?
    set -e
    
    if [ $PUBLIC_EXIT -eq 0 ]; then
        echo -e "${GREEN}✓${NC} Public access enabled"
        echo -e "${GREEN}➜${NC} Open: ${AGENT_URL}"
    else
        echo -e "${RED}✗${NC} Failed to enable public access"
        echo "$PUBLIC_ACCESS_OUTPUT"
    fi
else
    echo -e "${YELLOW}➜${NC} Use: gcloud run services proxy ${AGENT_SERVICE_NAME} --region=${REGION} --port=8080"
    echo -e "${YELLOW}➜${NC} Then: http://localhost:8080"
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Deployment Complete! 🎉           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Service:${NC} ${AGENT_SERVICE_NAME}"
echo -e "${BLUE}Region:${NC} ${REGION}"
echo -e "${BLUE}URL:${NC} ${AGENT_URL}"
echo ""
echo -e "${BLUE}Logs:${NC} gcloud run services logs tail ${AGENT_SERVICE_NAME} --region=${REGION}"
echo -e "${BLUE}Describe:${NC} gcloud run services describe ${AGENT_SERVICE_NAME} --region=${REGION}"
