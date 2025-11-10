#!/bin/bash

# Maps MCP Server Deployment Script
# Simple deployment to Google Cloud Run

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="formare-ai"
REGION="europe-west1"
SERVICE_NAME="factory-ai-agent-competition-mcp-server"
SERVICE_ACCOUNT_NAME="factory-comp-mcp-sa"

# Load .env file if it exists
if [ -f .env ]; then
    echo -e "${BLUE}Loading environment variables from .env file...${NC}"
    set -a  # automatically export all variables
    source .env
    set +a
    echo -e "${GREEN}✓ Environment variables loaded${NC}"
fi

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

section_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Validate prerequisites
validate_prerequisites() {
    section_header "Validating Prerequisites"
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed"
        exit 1
    fi
    log_success "gcloud CLI found"
    
    # Check if authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
        log_error "Not authenticated with gcloud. Run: gcloud auth login"
        exit 1
    fi
    log_success "Authenticated with gcloud"
    
    # Get current user email
    CURRENT_USER=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
    log_success "Current user: ${CURRENT_USER}"
    
    # Verify project exists and user has access
    if ! gcloud projects describe ${PROJECT_ID} &> /dev/null; then
        log_error "Cannot access project ${PROJECT_ID}"
        log_info "Run: gcloud config set project ${PROJECT_ID}"
        exit 1
    fi
    log_success "Project ${PROJECT_ID} accessible"
    
    # Check for required environment variables
    if [ -z "${GOOGLE_MAPS_API_KEY:-}" ]; then
        log_error "GOOGLE_MAPS_API_KEY environment variable is not set"
        echo ""
        echo -e "${YELLOW}Add it to your .env file:${NC}"
        echo -e "  GOOGLE_MAPS_API_KEY=your-key"
        echo ""
        exit 1
    fi
    log_success "GOOGLE_MAPS_API_KEY is set"
    
    if [ -z "${API_KEY_TARGETARE:-}" ]; then
        log_error "API_KEY_TARGETARE environment variable is not set"
        echo ""
        echo -e "${YELLOW}Add it to your .env file:${NC}"
        echo -e "  API_KEY_TARGETARE=your-key"
        echo ""
        exit 1
    fi
    log_success "API_KEY_TARGETARE is set"
    
    if [ -z "${GOOGLE_CUSTOM_SEARCH_API_KEY:-}" ]; then
        log_error "GOOGLE_CUSTOM_SEARCH_API_KEY environment variable is not set"
        echo ""
        echo -e "${YELLOW}Add it to your .env file:${NC}"
        echo -e "  GOOGLE_CUSTOM_SEARCH_API_KEY=your-key"
        echo ""
        exit 1
    fi
    log_success "GOOGLE_CUSTOM_SEARCH_API_KEY is set"
    
    if [ -z "${GOOGLE_CUSTOM_SEARCH_CX:-}" ]; then
        log_error "GOOGLE_CUSTOM_SEARCH_CX environment variable is not set"
        echo ""
        echo -e "${YELLOW}Add it to your .env file:${NC}"
        echo -e "  GOOGLE_CUSTOM_SEARCH_CX=your-search-engine-id"
        echo ""
        exit 1
    fi
    log_success "GOOGLE_CUSTOM_SEARCH_CX is set"
    
    # Check if server.py exists
    if [ ! -f "competition-mcp-server.py" ]; then
        log_error "competition-mcp-server.py not found in current directory"
        exit 1
    fi
    log_success "competition-mcp-server.py found"

}

# Enable required APIs
enable_apis() {
    section_header "STEP 1: Enable Google Cloud APIs"
    
    log_info "Enabling required APIs..."
    gcloud services enable \
        run.googleapis.com \
        cloudbuild.googleapis.com \
        iam.googleapis.com \
        --project=${PROJECT_ID}
    
    log_success "APIs enabled"
}

# Setup service account
setup_service_account() {
    section_header "STEP 2: Setup Service Account"
    
    local SA_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    # Check if service account exists
    log_info "Checking if service account exists..."
    if gcloud iam service-accounts describe ${SA_EMAIL} --project=${PROJECT_ID} &> /dev/null; then
        log_warning "Service account already exists"
    else
        # Create service account
        log_info "Creating service account..."
        gcloud iam service-accounts create ${SERVICE_ACCOUNT_NAME} \
            --display-name="Competition MCP Server" \
            --project=${PROJECT_ID}
        log_success "Service account created: ${SA_EMAIL}"
    fi
    
    # Grant the current user permission to act as the service account
    log_info "Granting Service Account User role to ${CURRENT_USER}..."
    gcloud iam service-accounts add-iam-policy-binding ${SA_EMAIL} \
        --member="user:${CURRENT_USER}" \
        --role="roles/iam.serviceAccountUser" \
        --project=${PROJECT_ID}
    log_success "Permission granted"
    
    # Grant the service account Cloud Run Invoker role
    log_info "Granting Cloud Run Invoker role to service account..."
    gcloud projects add-iam-policy-binding ${PROJECT_ID} \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="roles/run.invoker" \
        --condition=None
    log_success "Service account configured"
}

# Deploy to Cloud Run
deploy_cloud_run() {
    section_header "STEP 3: Deploy to Cloud Run"
    
    local SA_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    log_info "Deploying ${SERVICE_NAME} to Cloud Run..."
    log_info "Region: ${REGION}"
    log_info "This may take 2-5 minutes..."
    
    # Build environment variables string (all required)
    ENV_VARS="GOOGLE_MAPS_API_KEY=${GOOGLE_MAPS_API_KEY},API_KEY_TARGETARE=${API_KEY_TARGETARE},GOOGLE_CUSTOM_SEARCH_API_KEY=${GOOGLE_CUSTOM_SEARCH_API_KEY},GOOGLE_CUSTOM_SEARCH_CX=${GOOGLE_CUSTOM_SEARCH_CX}"
    
    if gcloud run deploy ${SERVICE_NAME} \
        --source . \
        --region=${REGION} \
        --platform=managed \
        --allow-unauthenticated \
        --service-account=${SA_EMAIL} \
        --set-env-vars "${ENV_VARS}" \
        --project=${PROJECT_ID} \
        --memory=32Gi \
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
        --quiet; then
        log_success "Deployment successful!"
    else
        log_error "Deployment failed"
        exit 1
    fi
}

# Get service URL
get_service_url() {
    section_header "STEP 4: Getting Service URL"
    
    log_info "Fetching service URL..."
    
    MCP_SERVER_URL=$(gcloud run services describe ${SERVICE_NAME} \
        --region=${REGION} \
        --project=${PROJECT_ID} \
        --format='value(status.url)')
    
    if [ -z "$MCP_SERVER_URL" ]; then
        log_error "Failed to get service URL"
        exit 1
    fi
    
    log_success "Service URL retrieved"
}

# Display summary
display_summary() {
    section_header "DEPLOYMENT COMPLETE"
    
    echo ""
    echo -e "${GREEN}MCP Server Details:${NC}"
    echo "========================================"
    echo -e "Service Name:    ${SERVICE_NAME}"
    echo -e "Region:          ${REGION}"
    echo -e "Project:         ${PROJECT_ID}"
    echo -e "Service URL:     ${MCP_SERVER_URL}"
    echo -e "SSE Endpoint:    ${MCP_SERVER_URL}/sse"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "========================================"
    echo "1. Test the MCP server:"
    echo "   gcloud run services proxy ${SERVICE_NAME} --region=${REGION} --port=8080"
    echo ""
    echo "2. In another terminal, test with curl:"
    echo "   curl http://localhost:8080/sse"
    echo ""
    echo "3. View logs:"
    echo "   gcloud run services logs read ${SERVICE_NAME} --region=${REGION}"
    echo ""
    echo "4. To update environment variables:"
    echo "   gcloud run services update ${SERVICE_NAME} --region=${REGION} \\"
    echo "     --set-env-vars GOOGLE_MAPS_API_KEY=your_key"
    echo ""
}

# Main execution
main() {
    echo -e "${BLUE}"
    echo "==========================================="
    echo "   Competition MCP Server Deployment"
    echo "==========================================="
    echo -e "${NC}"
    
    validate_prerequisites
    enable_apis
    setup_service_account
    deploy_cloud_run
    get_service_url
    display_summary
    
    echo ""
    log_success "All done!"
}

# Run main function
main