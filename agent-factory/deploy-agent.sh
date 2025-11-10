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
REGION="europe-west1"
AGENT_SERVICE_NAME="pandas-agent-backend"
MCP_SERVICE_NAME="pandas-agent-mcp-server"
AGENT_SERVICE_ACCOUNT="pandas-agent-sa"

echo -e "${BLUE}╔═══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   ADK Pandas Agent Deployment       ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════╝${NC}"
echo ""

# Validate files
echo -e "${BLUE}[1/6]${NC} Validating files..."
for file in main.py requirements.txt PandasDataScienceAssistant/agent.py; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}✗${NC} Missing: $file"
        exit 1
    fi
done

if [ ! -f "PandasDataScienceAssistant/__init__.py" ]; then
    echo "from . import agent" > PandasDataScienceAssistant/__init__.py
fi
echo -e "${GREEN}✓${NC} All files present"

# Get MCP server URL
echo -e "${BLUE}[2/6]${NC} Getting MCP server URL..."
MCP_SERVER_URL=$(gcloud run services describe ${MCP_SERVICE_NAME} \
    --region=${REGION} \
    --format='value(status.url)' 2>/dev/null)

if [ -z "$MCP_SERVER_URL" ]; then
    echo -e "${RED}✗${NC} MCP server not found!"
    exit 1
fi
MCP_SERVER_URL="${MCP_SERVER_URL}/sse"
echo -e "${GREEN}✓${NC} MCP: ${MCP_SERVER_URL}"

# Setup service account
echo -e "${BLUE}[3/6]${NC} Setting up service account..."
gcloud iam service-accounts create ${AGENT_SERVICE_ACCOUNT} \
    --display-name="Pandas ADK Agent" 2>/dev/null || true

# Grant Vertex AI access
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${AGENT_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user" \
    --quiet 2>/dev/null || true

# Grant MCP server access
gcloud run services add-iam-policy-binding ${MCP_SERVICE_NAME} \
    --region=${REGION} \
    --member="serviceAccount:${AGENT_SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/run.invoker" \
    --quiet 2>/dev/null || true

echo -e "${GREEN}✓${NC} Service account ready"

# Deploy
echo -e "${BLUE}[4/6]${NC} Deploying to Cloud Run..."
echo -e "${YELLOW}⏳${NC} This takes 2-4 minutes..."

gcloud run deploy ${AGENT_SERVICE_NAME} \
    --source . \
    --region=${REGION} \
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
    --min-instances=0 \
    --max-instances=3 \
    --no-cpu-throttling \
    --cpu-boost \
    --project=${PROJECT_ID} \
    --quiet

echo -e "${GREEN}✓${NC} Deployed!"

# Get URL
echo -e "${BLUE}[5/6]${NC} Getting URL..."
AGENT_URL=$(gcloud run services describe ${AGENT_SERVICE_NAME} \
    --region=${REGION} \
    --format='value(status.url)')

echo -e "${GREEN}✓${NC} URL: ${AGENT_URL}"

# Configure access
echo ""
echo -e "${BLUE}[6/6]${NC} Configure access..."
read -p "Enable public access? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    gcloud run services add-iam-policy-binding ${AGENT_SERVICE_NAME} \
        --region=${REGION} \
        --member="allUsers" \
        --role="roles/run.invoker" \
        --quiet
    echo -e "${GREEN}✓${NC} Public access enabled"
    echo -e "${GREEN}➜${NC} Open: ${AGENT_URL}"
else
    echo -e "${YELLOW}➜${NC} Use: gcloud run services proxy ${AGENT_SERVICE_NAME} --region=${REGION} --port=8080"
    echo -e "${YELLOW}➜${NC} Then: http://localhost:8080"
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Deployment Complete! 🎉           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Logs:${NC} gcloud run services logs tail ${AGENT_SERVICE_NAME} --region=${REGION}"