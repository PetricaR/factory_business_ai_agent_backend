#!/bin/bash

# Cloud Run Utility Script
# =========================
# Helper commands for managing Cloud Run services

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
SERVICE_NAME="${APP_NAME:-agent-factory-ai}"
REGION="${GCP_REGION:-europe-west4}"
PROJECT_ID="${GCP_PROJECT_ID:-formare-ai}"
PLATFORM="${PLATFORM:-managed}"

# Helper functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =======================================
# Commands
# =======================================

# View service logs
logs() {
    local limit=${1:-100}
    print_info "Viewing logs (last $limit lines)..."
    gcloud run services logs read "$SERVICE_NAME" \
        --platform="$PLATFORM" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --limit="$limit"
}

# Get service URL
url() {
    print_info "Getting service URL..."
    gcloud run services describe "$SERVICE_NAME" \
        --platform="$PLATFORM" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format='value(status.url)'
}

# Get service status
status() {
    print_info "Service status:"
    gcloud run services describe "$SERVICE_NAME" \
        --platform="$PLATFORM" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format='table(status.url,status.traffic[0].revisionName,status.conditions[0].status,spec.template.spec.containers[0].resources.limits.memory,spec.template.spec.containers[0].resources.limits.cpu)'
}

# List all revisions
revisions() {
    print_info "Service revisions:"
    gcloud run revisions list \
        --service="$SERVICE_NAME" \
        --platform="$PLATFORM" \
        --region="$REGION" \
        --project="$PROJECT_ID"
}

# Scale service
scale() {
    local min_instances=${1:-0}
    local max_instances=${2:-10}
    print_info "Scaling service to min=$min_instances, max=$max_instances..."
    gcloud run services update "$SERVICE_NAME" \
        --platform="$PLATFORM" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --min-instances="$min_instances" \
        --max-instances="$max_instances"
}

# Update environment variables
set_env() {
    local env_vars="$1"
    print_info "Setting environment variables: $env_vars"
    gcloud run services update "$SERVICE_NAME" \
        --platform="$PLATFORM" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --set-env-vars="$env_vars"
}

# Update memory
set_memory() {
    local memory="$1"
    print_info "Setting memory to $memory..."
    gcloud run services update "$SERVICE_NAME" \
        --platform="$PLATFORM" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --memory="$memory"
}

# Update CPU
set_cpu() {
    local cpu="$1"
    print_info "Setting CPU to $cpu..."
    gcloud run services update "$SERVICE_NAME" \
        --platform="$PLATFORM" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --cpu="$cpu"
}

# Rollback to previous revision
rollback() {
    print_info "Rolling back to previous revision..."
    local previous_revision=$(gcloud run revisions list \
        --service="$SERVICE_NAME" \
        --platform="$PLATFORM" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format='value(metadata.name)' \
        --limit=2 | tail -1)
    
    if [ -z "$previous_revision" ]; then
        print_error "No previous revision found"
        exit 1
    fi
    
    print_info "Rolling back to: $previous_revision"
    gcloud run services update-traffic "$SERVICE_NAME" \
        --platform="$PLATFORM" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --to-revisions="$previous_revision=100"
}

# Delete service
delete() {
    print_error "WARNING: This will delete the service $SERVICE_NAME"
    read -p "Are you sure? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        gcloud run services delete "$SERVICE_NAME" \
            --platform="$PLATFORM" \
            --region="$REGION" \
            --project="$PROJECT_ID"
        print_info "Service deleted"
    else
        print_info "Cancelled"
    fi
}

# Show help
help() {
    echo "Cloud Run Utility Commands"
    echo ""
    echo "Usage: ./utils.sh COMMAND [ARGS]"
    echo ""
    echo "Commands:"
    echo "  logs [LIMIT]           View service logs (default: 100 lines)"
    echo "  url                    Get service URL"
    echo "  status                 Get service status"
    echo "  revisions              List all revisions"
    echo "  scale MIN MAX          Scale service (e.g., ./utils.sh scale 1 10)"
    echo "  set-env VARS           Set environment variables (e.g., KEY1=value1,KEY2=value2)"
    echo "  set-memory MEMORY      Update memory (e.g., 2Gi)"
    echo "  set-cpu CPU            Update CPU (e.g., 2)"
    echo "  rollback               Rollback to previous revision"
    echo "  delete                 Delete service"
    echo "  help                   Show this help"
    echo ""
    echo "Examples:"
    echo "  ./utils.sh logs 200"
    echo "  ./utils.sh scale 1 5"
    echo "  ./utils.sh set-env API_KEY=123,DEBUG=true"
    echo "  ./utils.sh set-memory 2Gi"
}

# =======================================
# Main
# =======================================

COMMAND=${1:-help}

case "$COMMAND" in
    logs)
        logs "${2:-100}"
        ;;
    url)
        url
        ;;
    status)
        status
        ;;
    revisions)
        revisions
        ;;
    scale)
        if [ -z "$2" ] || [ -z "$3" ]; then
            print_error "Usage: $0 scale MIN_INSTANCES MAX_INSTANCES"
            exit 1
        fi
        scale "$2" "$3"
        ;;
    set-env)
        if [ -z "$2" ]; then
            print_error "Usage: $0 set-env KEY1=value1,KEY2=value2"
            exit 1
        fi
        set_env "$2"
        ;;
    set-memory)
        if [ -z "$2" ]; then
            print_error "Usage: $0 set-memory MEMORY (e.g., 2Gi)"
            exit 1
        fi
        set_memory "$2"
        ;;
    set-cpu)
        if [ -z "$2" ]; then
            print_error "Usage: $0 set-cpu CPU (e.g., 2)"
            exit 1
        fi
        set_cpu "$2"
        ;;
    rollback)
        rollback
        ;;
    delete)
        delete
        ;;
    help|*)
        help
        ;;
esac
