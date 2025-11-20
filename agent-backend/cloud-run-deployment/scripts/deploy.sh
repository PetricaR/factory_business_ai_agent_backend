#!/bin/bash

# Cloud Run Deployment Script
# ============================
# Complete deployment pipeline for deploying to Google Cloud Run

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =======================================
# Configuration
# =======================================

PROJECT_ID="${GCP_PROJECT_ID:-formare-ai}"
REGION="${GCP_REGION:-europe-west4}"

# Application Configuration
APP_NAME="${APP_NAME:-agent-factory-ai}"
SERVICE_NAME="${SERVICE_NAME:-$APP_NAME}"

# Cloud Run Configuration
PLATFORM="${PLATFORM:-managed}"
ALLOW_UNAUTHENTICATED="${ALLOW_UNAUTHENTICATED:-true}"

# Resource Configuration
MEMORY="${MEMORY:-1Gi}"
CPU="${CPU:-1}"
MAX_INSTANCES="${MAX_INSTANCES:-10}"
MIN_INSTANCES="${MIN_INSTANCES:-0}"
TIMEOUT="${TIMEOUT:-300}"
CONCURRENCY="${CONCURRENCY:-80}"

# Registry Configuration
REGISTRY_TYPE="${REGISTRY_TYPE:-gcr}"
AR_LOCATION="${AR_LOCATION:-$REGION}"
AR_REPOSITORY="${AR_REPOSITORY:-docker-repo}"

# Build Configuration
BUILD_CONTEXT="${BUILD_CONTEXT:-..}"

# =======================================
# Helper Functions
# =======================================

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# =======================================
# Check Prerequisites
# =======================================

check_prerequisites() {
    print_header "Checking Prerequisites"
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI is not installed"
        exit 1
    fi
    
    print_success "All prerequisites met"
}

# =======================================
# Get Image URL
# =======================================

get_image_url() {
    local tag=$1
    
    if [ "$REGISTRY_TYPE" == "gcr" ]; then
        echo "gcr.io/${PROJECT_ID}/${APP_NAME}:${tag}"
    elif [ "$REGISTRY_TYPE" == "artifact-registry" ]; then
        echo "${AR_LOCATION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPOSITORY}/${APP_NAME}:${tag}"
    fi
}

# =======================================
# Configure Docker Authentication
# =======================================

configure_docker_auth() {
    print_header "Configuring Docker Authentication"
    
    if [ "$REGISTRY_TYPE" == "gcr" ]; then
        gcloud auth configure-docker --quiet
    elif [ "$REGISTRY_TYPE" == "artifact-registry" ]; then
        gcloud auth configure-docker ${AR_LOCATION}-docker.pkg.dev --quiet
    fi
    
    print_success "Docker authentication configured"
}

# =======================================
# Build Docker Image
# =======================================

build_image() {
    print_header "Building Docker Image"
    
    local tag=$(date +%Y%m%d-%H%M%S)
    local image_url=$(get_image_url "$tag")
    local latest_url=$(get_image_url "latest")
    
    print_info "Building for platform: linux/amd64"
    print_info "Image: $image_url"
    
    docker build \
        --platform=linux/amd64 \
        -t "$image_url" \
        -t "$latest_url" \
        "$BUILD_CONTEXT"
    
    export IMAGE_TAG="$tag"
    export IMAGE_URL="$image_url"
    export LATEST_URL="$latest_url"
    
    print_success "Docker image built"
}

# =======================================
# Push Docker Image
# =======================================

push_image() {
    print_header "Pushing Docker Image"
    
    print_info "Pushing $IMAGE_URL"
    docker push "$IMAGE_URL"
    
    print_info "Pushing $LATEST_URL"
    docker push "$LATEST_URL"
    
    print_success "Docker image pushed"
}

# =======================================
# Deploy to Cloud Run
# =======================================

deploy_to_cloud_run() {
    print_header "Deploying to Cloud Run"
    
    print_info "Service: $SERVICE_NAME"
    print_info "Region: $REGION"
    print_info "Image: $IMAGE_URL"
    
    local deploy_cmd="gcloud run deploy $SERVICE_NAME \
        --image=$IMAGE_URL \
        --platform=$PLATFORM \
        --region=$REGION \
        --project=$PROJECT_ID \
        --memory=$MEMORY \
        --cpu=$CPU \
        --timeout=$TIMEOUT \
        --concurrency=$CONCURRENCY \
        --max-instances=$MAX_INSTANCES \
        --min-instances=$MIN_INSTANCES \
        --port=8080"
    
    if [ "$ALLOW_UNAUTHENTICATED" == "true" ]; then
        deploy_cmd="$deploy_cmd --allow-unauthenticated"
    else
        deploy_cmd="$deploy_cmd --no-allow-unauthenticated"
    fi
    
    print_info "Deploying..."
    eval $deploy_cmd
    
    print_success "Cloud Run deployment completed"
}

# =======================================
# Get Service Information
# =======================================

get_service_info() {
    print_header "Service Information"
    
    # Get service URL
    local service_url=$(gcloud run services describe $SERVICE_NAME \
        --platform=$PLATFORM \
        --region=$REGION \
        --project=$PROJECT_ID \
        --format='value(status.url)')
    
    echo -e "${GREEN}Service Details:${NC}"
    gcloud run services describe $SERVICE_NAME \
        --platform=$PLATFORM \
        --region=$REGION \
        --project=$PROJECT_ID \
        --format='table(status.url,status.traffic[0].revisionName,spec.template.spec.containers[0].resources.limits.memory,spec.template.spec.containers[0].resources.limits.cpu)'
    
    if [ -n "$service_url" ]; then
        echo -e "\n${GREEN}✓ Service URL: ${NC}$service_url"
        echo -e "${GREEN}✓ Access your app at: ${NC}$service_url"
        echo -e "${GREEN}✓ Health check: ${NC}$service_url/health"
        echo -e "${GREEN}✓ API docs: ${NC}$service_url/docs"
        export SERVICE_URL="$service_url"
    fi
}

# =======================================
# Print Summary
# =======================================

print_summary() {
    print_header "Deployment Complete!"
    
    echo -e "${GREEN}✓ Project: ${NC}$PROJECT_ID"
    echo -e "${GREEN}✓ Region: ${NC}$REGION"
    echo -e "${GREEN}✓ Service: ${NC}$SERVICE_NAME"
    echo -e "${GREEN}✓ Image: ${NC}$IMAGE_URL"
    echo -e "${GREEN}✓ Platform: ${NC}$PLATFORM"
    
    if [ -n "$SERVICE_URL" ]; then
        echo -e "\n${YELLOW}Access URLs:${NC}"
        echo "  Main:     $SERVICE_URL"
        echo "  Health:   $SERVICE_URL/health"
        echo "  API Docs: $SERVICE_URL/docs"
        echo "  Info:     $SERVICE_URL/info"
    fi
    
    echo -e "\n${YELLOW}Useful Commands:${NC}"
    echo "  View logs:    gcloud run services logs read $SERVICE_NAME --region=$REGION --limit=100"
    echo "  Update:       Re-run this script"
    echo "  Scale:        gcloud run services update $SERVICE_NAME --min-instances=N --region=$REGION"
    echo "  Delete:       gcloud run services delete $SERVICE_NAME --region=$REGION"
}

# =======================================
# Main Execution
# =======================================

main() {
    print_header "Cloud Run Deployment Pipeline"
    
    echo "Configuration:"
    echo "  Project:      $PROJECT_ID"
    echo "  Region:       $REGION"
    echo "  Service:      $SERVICE_NAME"
    echo "  Platform:     $PLATFORM"
    echo "  Memory:       $MEMORY"
    echo "  CPU:          $CPU"
    echo "  Max Instances: $MAX_INSTANCES"
    echo "  Min Instances: $MIN_INSTANCES"
    echo ""
    
    read -p "Continue with deployment? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Aborted by user"
        exit 0
    fi
    
    check_prerequisites
    gcloud config set project "$PROJECT_ID"
    configure_docker_auth
    build_image
    push_image
    deploy_to_cloud_run
    get_service_info
    print_summary
}

# Run main function
main "$@"
