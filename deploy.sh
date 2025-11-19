#!/bin/bash

# GKE Deployment Script for Agent Backend
# ========================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration Variables
# ========================================
# Edit these variables according to your setup

# Google Cloud Settings
PROJECT_ID="${GCP_PROJECT_ID:-formare-ai}"
REGION="${GCP_REGION:-europe-west4}"
CLUSTER_NAME="${GKE_CLUSTER_NAME:-cluter-ai-agents}"
CLUSTER_ZONE="${GKE_CLUSTER_ZONE:-europe-west4-a}"

# Docker/Registry Settings
IMAGE_NAME="agent-factory-ai"
SERVICE_NAME="agent-factory-ai"
REGISTRY_TYPE="${REGISTRY_TYPE:-gcr}"  # Options: gcr, artifact-registry

# Artifact Registry Settings (if using Artifact Registry)
AR_LOCATION="${AR_LOCATION:-europe-west4}"
AR_REPOSITORY="${AR_REPOSITORY:-docker-repo}"

# Kubernetes Settings
NAMESPACE="${K8S_NAMESPACE:-default}"
DEPLOYMENT_FILE="k8s/deployment.yaml"
SERVICE_FILE="k8s/service.yaml"

# Build Settings
BUILD_CONTEXT="./agent-backend"

# ========================================
# Helper Functions
# ========================================

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed. Please install it first."
        exit 1
    fi
    
    # Check if gke-gcloud-auth-plugin is installed
    if ! command -v gke-gcloud-auth-plugin &> /dev/null; then
        print_error "gke-gcloud-auth-plugin is not installed. Install it with:"
        print_error "  gcloud components install gke-gcloud-auth-plugin"
        exit 1
    fi
    
    print_info "All prerequisites met ✓"
}

configure_gcloud() {
    print_info "Configuring gcloud..."
    
    # Set project
    gcloud config set project "$PROJECT_ID"
    
    # Set region
    gcloud config set compute/region "$REGION"
    
    print_info "gcloud configured ✓"
}

get_image_url() {
    local tag=$1
    
    if [ "$REGISTRY_TYPE" == "gcr" ]; then
        echo "gcr.io/${PROJECT_ID}/${IMAGE_NAME}:${tag}"
    elif [ "$REGISTRY_TYPE" == "artifact-registry" ]; then
        echo "${AR_LOCATION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPOSITORY}/${IMAGE_NAME}:${tag}"
    else
        print_error "Invalid REGISTRY_TYPE: $REGISTRY_TYPE"
        exit 1
    fi
}

configure_docker_auth() {
    print_info "Configuring Docker authentication..."
    
    if [ "$REGISTRY_TYPE" == "gcr" ]; then
        gcloud auth configure-docker --quiet
    elif [ "$REGISTRY_TYPE" == "artifact-registry" ]; then
        gcloud auth configure-docker ${AR_LOCATION}-docker.pkg.dev --quiet
    fi
    
    print_info "Docker authentication configured ✓"
}

build_image() {
    local tag=$1
    local image_url=$(get_image_url "$tag")
    
    print_info "Building Docker image: $image_url"
    
    docker build --platform=linux/amd64 -t "$image_url" "$BUILD_CONTEXT"
    
    # Also tag as latest
    local latest_url=$(get_image_url "latest")
    docker tag "$image_url" "$latest_url"
    
    print_info "Docker image built ✓"
}

push_image() {
    local tag=$1
    local image_url=$(get_image_url "$tag")
    local latest_url=$(get_image_url "latest")
    
    print_info "Pushing Docker image to registry..."
    
    docker push "$image_url"
    docker push "$latest_url"
    
    print_info "Docker image pushed ✓"
}

get_cluster_credentials() {
    print_info "Getting GKE cluster credentials..."
    
    gcloud container clusters get-credentials "$CLUSTER_NAME" \
        --region "$REGION" \
        --project "$PROJECT_ID"
    
    print_info "Cluster credentials obtained ✓"
}

create_namespace_if_needed() {
    if [ "$NAMESPACE" != "default" ]; then
        print_info "Ensuring namespace '$NAMESPACE' exists..."
        
        if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
            kubectl create namespace "$NAMESPACE"
            print_info "Namespace created ✓"
        else
            print_info "Namespace already exists ✓"
        fi
    fi
}

deploy_to_k8s() {
    local tag=$1
    local image_url=$(get_image_url "$tag")
    
    print_info "Deploying to Kubernetes..."
    
    if [ -f "$DEPLOYMENT_FILE" ]; then
        # Use existing deployment file
        print_info "Using deployment file: $DEPLOYMENT_FILE"
        
        # Replace image in deployment file and apply
        cat "$DEPLOYMENT_FILE" | sed "s|IMAGE_URL_PLACEHOLDER|$image_url|g" | kubectl apply -n "$NAMESPACE" -f -
        
        # Apply service if it exists
        if [ -f "$SERVICE_FILE" ]; then
            print_info "Applying service file: $SERVICE_FILE"
            kubectl apply -n "$NAMESPACE" -f "$SERVICE_FILE"
        fi
    else
        # Create deployment on-the-fly
        print_warning "No deployment file found at $DEPLOYMENT_FILE"
        print_info "Creating deployment using kubectl create..."
        
        # Check if deployment exists
        if kubectl get deployment "$SERVICE_NAME" -n "$NAMESPACE" &> /dev/null; then
            # Update existing deployment
            kubectl set image deployment/"$SERVICE_NAME" \
                "${SERVICE_NAME}=${image_url}" \
                -n "$NAMESPACE"
        else
            # Create new deployment
            kubectl create deployment "$SERVICE_NAME" \
                --image="$image_url" \
                -n "$NAMESPACE"
            
            # Expose the deployment
            kubectl expose deployment "$SERVICE_NAME" \
                --type=LoadBalancer \
                --port=80 \
                --target-port=8080 \
                -n "$NAMESPACE"
        fi
    fi
    
    print_info "Deployment updated ✓"
}

wait_for_rollout() {
    print_info "Waiting for rollout to complete..."
    
    kubectl rollout status deployment/"$SERVICE_NAME" -n "$NAMESPACE"
    
    print_info "Rollout completed ✓"
}

get_service_info() {
    print_info "Getting service information..."
    
    kubectl get service "$SERVICE_NAME" -n "$NAMESPACE"
    
    print_info "\nTo get the external IP (may take a few minutes):"
    print_info "  kubectl get service $SERVICE_NAME -n $NAMESPACE"
}

# ========================================
# Main Execution
# ========================================

main() {
    print_info "Starting deployment process..."
    echo ""
    
    # Generate tag using timestamp
    TAG=$(date +%Y%m%d-%H%M%S)
    
    print_info "Deployment Configuration:"
    echo "  Project ID:      $PROJECT_ID"
    echo "  Cluster Name:    $CLUSTER_NAME"
    echo "  Cluster Zone:    $CLUSTER_ZONE"
    echo "  Image Name:      $IMAGE_NAME"
    echo "  Image Tag:       $TAG"
    echo "  Registry Type:   $REGISTRY_TYPE"
    echo "  Namespace:       $NAMESPACE"
    echo "  Build Context:   $BUILD_CONTEXT"
    echo ""
    
    # Ask for confirmation
    read -p "Continue with deployment? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Deployment cancelled."
        exit 0
    fi
    
    # Execute deployment steps
    check_prerequisites
    configure_gcloud
    configure_docker_auth
    build_image "$TAG"
    push_image "$TAG"
    get_cluster_credentials
    create_namespace_if_needed
    deploy_to_k8s "$TAG"
    wait_for_rollout
    get_service_info
    
    echo ""
    print_info "✅ Deployment completed successfully!"
    print_info "Image: $(get_image_url $TAG)"
}

# Run main function
main "$@"
