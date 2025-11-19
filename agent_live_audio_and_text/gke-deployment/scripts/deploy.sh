#!/bin/bash

# Application Deployment Script for agent_live_audio_and_text
# ============================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Load configuration
if [ -f "../config.env" ]; then
    source ../config.env
fi

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-formare-ai}"
REGION="${GCP_REGION:-europe-west4}"
CLUSTER_NAME="${CLUSTER_NAME:-ai-agents-cluster}"

# Application Configuration
APP_NAME="${APP_NAME:-agent-audio-text}"
IMAGE_NAME="$APP_NAME"
SERVICE_NAME="$APP_NAME"
NAMESPACE="${K8S_NAMESPACE:-default}"

# Registry Configuration
REGISTRY_TYPE="${REGISTRY_TYPE:-gcr}"
AR_LOCATION="${AR_LOCATION:-$REGION}"
AR_REPOSITORY="${AR_REPOSITORY:-docker-repo}"

# Build Configuration
BUILD_CONTEXT="../../"  # Build from agent_live_audio_and_text root
DEPLOYMENT_DIR="../k8s"

# Helper Functions
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed"
        exit 1
    fi
    
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI is not installed"
        exit 1
    fi
    
    print_info "All prerequisites met ✓"
}

get_image_url() {
    local tag=$1
    
    if [ "$REGISTRY_TYPE" == "gcr" ]; then
        echo "gcr.io/${PROJECT_ID}/${IMAGE_NAME}:${tag}"
    elif [ "$REGISTRY_TYPE" == "artifact-registry" ]; then
        echo "${AR_LOCATION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPOSITORY}/${IMAGE_NAME}:${tag}"
    fi
}

configure_docker_auth() {
    print_header "Configuring Docker Authentication"
    
    if [ "$REGISTRY_TYPE" == "gcr" ]; then
        gcloud auth configure-docker --quiet
    elif [ "$REGISTRY_TYPE" == "artifact-registry" ]; then
        gcloud auth configure-docker ${AR_LOCATION}-docker.pkg.dev --quiet
    fi
    
    print_info "Docker authentication configured ✓"
}

build_image() {
    print_header "Building Docker Image"
    
    local tag=$(date +%Y%m%d-%H%M%S)
    local image_url=$(get_image_url "$tag")
    local latest_url=$(get_image_url "latest")
    
    print_info "Building for platform: linux/amd64"
    print_info "Image: $image_url"
    print_info "Context: $BUILD_CONTEXT"
    
    docker build \
        --platform=linux/amd64 \
        -t "$image_url" \
        -t "$latest_url" \
        "$BUILD_CONTEXT"
    
    export IMAGE_TAG="$tag"
    export IMAGE_URL="$image_url"
    export LATEST_URL="$latest_url"
    
    print_info "Docker image built ✓"
}

push_image() {
    print_header "Pushing Docker Image"
    
    print_info "Pushing $IMAGE_URL"
    docker push "$IMAGE_URL"
    
    print_info "Pushing $LATEST_URL"
    docker push "$LATEST_URL"
    
    print_info "Docker image pushed ✓"
}

get_cluster_credentials() {
    print_header "Getting Cluster Credentials"
    
    gcloud container clusters get-credentials "$CLUSTER_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID"
    
    print_info "Credentials obtained ✓"
}

deploy_to_kubernetes() {
    print_header "Deploying to Kubernetes"
    
    # Apply deployment
    if [ -f "$DEPLOYMENT_DIR/deployment.yaml" ]; then
        print_info "Applying deployment..."
        cat "$DEPLOYMENT_DIR/deployment.yaml" | \
            sed "s|IMAGE_URL_PLACEHOLDER|$IMAGE_URL|g" | \
            kubectl apply -n "$NAMESPACE" -f -
    else
        print_error "Deployment file not found: $DEPLOYMENT_DIR/deployment.yaml"
        print_info "Generate it with: ./0-generate-k8s-manifests.sh"
        exit 1
    fi
    
    # Apply service
    if [ -f "$DEPLOYMENT_DIR/service.yaml" ]; then
        print_info "Applying service..."
        kubectl apply -n "$NAMESPACE" -f "$DEPLOYMENT_DIR/service.yaml"
    fi
    
    print_info "Kubernetes resources applied ✓"
}

wait_for_rollout() {
    print_header "Waiting for Rollout"
    
    print_info "Waiting for deployment to be ready..."
    kubectl rollout status deployment/"$SERVICE_NAME" -n "$NAMESPACE" --timeout=5m
    
    print_info "Rollout completed ✓"
}

get_service_info() {
    print_header "Service Information"
    
    echo -e "${GREEN}Deployment:${NC}"
    kubectl get deployment "$SERVICE_NAME" -n "$NAMESPACE"
    
    echo -e "\n${GREEN}Pods:${NC}"
    kubectl get pods -l app="$SERVICE_NAME" -n "$NAMESPACE"
    
    echo -e "\n${GREEN}Service:${NC}"
    kubectl get service "$SERVICE_NAME" -n "$NAMESPACE"
    
    # Get external IP
    local external_ip=$(kubectl get service "$SERVICE_NAME" -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
    
    if [ -n "$external_ip" ]; then
        echo -e "\n${GREEN}✓ External IP: ${NC}$external_ip"
        echo -e "${GREEN}✓ Access your app at: ${NC}http://$external_ip"
        export EXTERNAL_IP="$external_ip"
    else
        print_warning "External IP not yet assigned. Run: kubectl get service $SERVICE_NAME -n $NAMESPACE"
    fi
}

print_summary() {
    print_header "Deployment Complete!"
    
    echo -e "${GREEN}✓ Project: ${NC}$PROJECT_ID"
    echo -e "${GREEN}✓ Cluster: ${NC}$CLUSTER_NAME ($REGION)"
    echo -e "${GREEN}✓ Image: ${NC}$IMAGE_URL"
    echo -e "${GREEN}✓ Namespace: ${NC}$NAMESPACE"
    echo -e "${GREEN}✓ Service: ${NC}$SERVICE_NAME"
    
    if [ -n "$EXTERNAL_IP" ]; then
        echo -e "\n${YELLOW}Access URLs:${NC}"
        echo "  Main:     http://$EXTERNAL_IP"
        echo "  Health:   http://$EXTERNAL_IP/health"
        echo "  API Docs: http://$EXTERNAL_IP/docs"
    fi
    
    echo -e "\n${YELLOW}Useful Commands:${NC}"
    echo "  View pods:   kubectl get pods -l app=$SERVICE_NAME"
    echo "  View logs:   kubectl logs -l app=$SERVICE_NAME --tail=100"
    echo "  Restart:     kubectl rollout restart deployment $SERVICE_NAME"
}

# Main Execution
main() {
    print_header "Deploy Agent Live Audio & Text"
    
    echo "Configuration:"
    echo "  Project:      $PROJECT_ID"
    echo "  Cluster:      $CLUSTER_NAME"
    echo "  Region:       $REGION"
    echo "  App:          $APP_NAME"
    echo "  Namespace:    $NAMESPACE"
    echo "  Registry:     $REGISTRY_TYPE"
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
    get_cluster_credentials
    deploy_to_kubernetes
    wait_for_rollout
    get_service_info
    print_summary
}

main "$@"
