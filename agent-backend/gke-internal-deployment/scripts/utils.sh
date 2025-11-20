#!/bin/bash

# Internal GKE Access Utility Script
# ===================================
# Helper commands for accessing internal GKE services

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SERVICE_NAME="${APP_NAME:-agent-factory-ai}"
NAMESPACE="${K8S_NAMESPACE:-default}"
PROJECT_ID="${GCP_PROJECT_ID:-formare-ai}"
CLUSTER_NAME="${CLUSTER_NAME:-ai-agents-cluster}"
REGION="${GCP_REGION:-europe-west4}"

# Helper functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# =======================================
# Port Forwarding
# =======================================

port_forward() {
    local local_port=${1:-8080}
    local remote_port=${2:-80}
    
    print_info "Setting up port forwarding..."
    print_info "  Local:  http://localhost:$local_port"
    print_info "  Remote: $SERVICE_NAME:$remote_port"
    print_warning "Press Ctrl+C to stop port forwarding"
    
    kubectl port-forward \
        -n "$NAMESPACE" \
        "service/$SERVICE_NAME" \
        "$local_port:$remote_port"
}

# =======================================
# Pod Port Forwarding (direct to pod)
# =======================================

pod_forward() {
    local local_port=${1:-8080}
    local remote_port=${2:-8080}
    
    print_info "Finding pod..."
    local pod=$(kubectl get pods -n "$NAMESPACE" -l "app=$SERVICE_NAME" -o jsonpath='{.items[0].metadata.name}')
    
    if [ -z "$pod" ]; then
        print_error "No pods found for app=$SERVICE_NAME"
        exit 1
    fi
    
    print_info "Port forwarding to pod: $pod"
    print_info "  Local:  http://localhost:$local_port"
    print_info "  Remote: pod:$remote_port"
    print_warning "Press Ctrl+C to stop port forwarding"
    
    kubectl port-forward \
        -n "$NAMESPACE" \
        "$pod" \
        "$local_port:$remote_port"
}

# =======================================
# Logs
# =======================================

logs() {
    local lines=${1:-100}
    print_info "Viewing logs (last $lines lines)..."
    kubectl logs \
        -l "app=$SERVICE_NAME" \
        -n "$NAMESPACE" \
        --tail="$lines" \
        --timestamps
}

# =======================================
# Follow Logs
# =======================================

logs_follow() {
    print_info "Following logs (Ctrl+C to stop)..."
    kubectl logs \
        -l "app=$SERVICE_NAME" \
        -n "$NAMESPACE" \
        --follow \
        --timestamps
}

# =======================================
# Status
# =======================================

status() {
    print_info "Service status:"
    kubectl get service "$SERVICE_NAME" -n "$NAMESPACE"
    
    echo ""
    print_info "Pods:"
    kubectl get pods -l "app=$SERVICE_NAME" -n "$NAMESPACE"
    
    echo ""
    print_info "Deployment:"
    kubectl get deployment "$SERVICE_NAME" -n "$NAMESPACE"
}

# =======================================
# Get Service IP (ClusterIP)
# =======================================

get_ip() {
    print_info "Getting ClusterIP..."
    local cluster_ip=$(kubectl get service "$SERVICE_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}')
    
    if [ -n "$cluster_ip" ]; then
        echo -e "${GREEN}ClusterIP: ${NC}$cluster_ip"
        echo -e "${YELLOW}Note: This IP is only accessible within the cluster${NC}"
        echo ""
        echo "To access from your machine, use port forwarding:"
        echo "  ./utils.sh forward"
    else
        print_error "Could not get ClusterIP"
    fi
}

# =======================================
# Shell into Pod
# =======================================

shell() {
    print_info "Finding pod..."
    local pod=$(kubectl get pods -n "$NAMESPACE" -l "app=$SERVICE_NAME" -o jsonpath='{.items[0].metadata.name}')
    
    if [ -z "$pod" ]; then
        print_error "No pods found for app=$SERVICE_NAME"
        exit 1
    fi
    
    print_info "Opening shell in pod: $pod"
    kubectl exec -it -n "$NAMESPACE" "$pod" -- /bin/bash || \
    kubectl exec -it -n "$NAMESPACE" "$pod" -- /bin/sh
}

# =======================================
# Scale
# =======================================

scale() {
    local replicas=${1:-2}
    print_info "Scaling deployment to $replicas replicas..."
    kubectl scale deployment "$SERVICE_NAME" \
        --replicas="$replicas" \
        -n "$NAMESPACE"
}

# =======================================
# Restart
# =======================================

restart() {
    print_info "Restarting deployment..."
    kubectl rollout restart deployment "$SERVICE_NAME" -n "$NAMESPACE"
    print_info "Waiting for rollout..."
    kubectl rollout status deployment "$SERVICE_NAME" -n "$NAMESPACE"
}

# =======================================
# Delete
# =======================================

delete() {
    print_error "WARNING: This will delete the deployment and service"
    read -p "Are you sure? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl delete deployment "$SERVICE_NAME" -n "$NAMESPACE"
        kubectl delete service "$SERVICE_NAME" -n "$NAMESPACE"
        print_info "Deployment and service deleted"
    else
        print_info "Cancelled"
    fi
}

# =======================================
# Create Tunnel (Cloud IAP)
# =======================================

tunnel() {
    print_info "Creating IAP tunnel..."
    print_info "This creates a secure tunnel through Cloud IAP"
    
    # Get cluster credentials first
    gcloud container clusters get-credentials "$CLUSTER_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" > /dev/null
    
    local local_port=${1:-8080}
    
    print_info "Starting kubectl proxy on port $local_port..."
    print_info "Access at: http://localhost:$local_port"
    
    kubectl proxy --port="$local_port"
}

# =======================================
# Help
# =======================================

help() {
    echo "Internal GKE Access Utility Commands"
    echo ""
    echo "Usage: ./utils.sh COMMAND [ARGS]"
    echo ""
    echo "Access Commands:"
    echo "  forward [LOCAL_PORT] [REMOTE_PORT]  Port forward to service (default: 8080:80)"
    echo "  pod-forward [LOCAL] [REMOTE]        Port forward to pod (default: 8080:8080)"
    echo "  tunnel [PORT]                       Create IAP tunnel (default: 8080)"
    echo "  shell                               Open shell in pod"
    echo ""
    echo "Monitoring Commands:"
    echo "  logs [LINES]                        View logs (default: 100 lines)"
    echo "  logs-follow                         Follow logs in real-time"
    echo "  status                              Get service/pod status"
    echo "  ip                                  Get ClusterIP"
    echo ""
    echo "Management Commands:"
    echo "  scale REPLICAS                      Scale deployment"
    echo "  restart                             Restart deployment"
    echo "  delete                              Delete deployment and service"
    echo "  help                                Show this help"
    echo ""
    echo "Examples:"
    echo "  # Forward service port 80 to localhost:8080"
    echo "  ./utils.sh forward"
    echo ""
    echo "  # Forward to different local port"
    echo "  ./utils.sh forward 9000 80"
    echo ""
    echo "  # Forward directly to pod"
    echo "  ./utils.sh pod-forward"
    echo ""
    echo "  # View last 200 log lines"
    echo "  ./utils.sh logs 200"
    echo ""
    echo "  # Open shell in pod"
    echo "  ./utils.sh shell"
}

# =======================================
# Main
# =======================================

COMMAND=${1:-help}

case "$COMMAND" in
    forward|port-forward)
        port_forward "${2:-8080}" "${3:-80}"
        ;;
    pod-forward)
        pod_forward "${2:-8080}" "${3:-8080}"
        ;;
    tunnel)
        tunnel "${2:-8080}"
        ;;
    logs)
        logs "${2:-100}"
        ;;
    logs-follow|follow)
        logs_follow
        ;;
    status)
        status
        ;;
    ip|cluster-ip)
        get_ip
        ;;
    shell|exec|bash)
        shell
        ;;
    scale)
        if [ -z "$2" ]; then
            print_error "Usage: $0 scale REPLICAS"
            exit 1
        fi
        scale "$2"
        ;;
    restart)
        restart
        ;;
    delete)
        delete
        ;;
    help|*)
        help
        ;;
esac
