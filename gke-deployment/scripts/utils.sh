#!/bin/bash

# Utility scripts for managing GKE deployments

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

# View Logs
view_logs() {
    local app_name="${1:-agent-factory-ai}"
    local namespace="${2:-default}"
    local lines="${3:-100}"
    
    print_info "Viewing logs for $app_name in namespace $namespace"
    kubectl logs -l app="$app_name" -n "$namespace" --tail="$lines" -f
}

# Scale Deployment
scale_deployment() {
    local app_name="${1:-agent-factory-ai}"
    local replicas="${2:-2}"
    local namespace="${3:-default}"
    
    print_info "Scaling $app_name to $replicas replicas"
    kubectl scale deployment "$app_name" --replicas="$replicas" -n "$namespace"
}

# Restart Deployment
restart_deployment() {
    local app_name="${1:-agent-factory-ai}"
    local namespace="${2:-default}"
    
    print_info "Restarting deployment $app_name"
    kubectl rollout restart deployment "$app_name" -n "$namespace"
    kubectl rollout status deployment "$app_name" -n "$namespace"
}

# Get External IP
get_external_ip() {
    local service_name="${1:-agent-factory-ai}"
    local namespace="${2:-default}"
    
    kubectl get service "$service_name" -n "$namespace" -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
}

# Delete Deployment
delete_deployment() {
    local app_name="${1:-agent-factory-ai}"
    local namespace="${2:-default}"
    
    echo -e "${YELLOW}WARNING: This will delete the deployment and service${NC}"
    read -p "Are you sure? (yes/no) " -r
    if [ "$REPLY" = "yes" ]; then
        kubectl delete deployment "$app_name" -n "$namespace"
        kubectl delete service "$app_name" -n "$namespace"
        print_info "Deleted $app_name"
    fi
}

# Show status
show_status() {
    local app_name="${1:-agent-factory-ai}"
    local namespace="${2:-default}"
    
    echo "Deployment:"
    kubectl get deployment "$app_name" -n "$namespace"
    echo ""
    echo "Pods:"
    kubectl get pods -l app="$app_name" -n "$namespace"
    echo ""
    echo "Service:"
    kubectl get service "$app_name" -n "$namespace"
    echo ""
    echo "External IP:"
    get_external_ip "$app_name" "$namespace"
}

# Main menu
case "${1:-help}" in
    logs)
        view_logs "$2" "$3" "$4"
        ;;
    scale)
        scale_deployment "$2" "$3" "$4"
        ;;
    restart)
        restart_deployment "$2" "$3"
        ;;
    ip)
        get_external_ip "$2" "$3"
        ;;
    delete)
        delete_deployment "$2" "$3"
        ;;
    status)
        show_status "$2" "$3"
        ;;
    help|*)
        echo "Usage: $0 {logs|scale|restart|ip|delete|status} [app_name] [namespace] [args]"
        echo ""
        echo "Commands:"
        echo "  logs [app] [namespace] [lines]  - View application logs"
        echo "  scale [app] [replicas] [ns]     - Scale deployment"
        echo "  restart [app] [namespace]       - Restart deployment"
        echo "  ip [service] [namespace]        - Get external IP"
        echo "  delete [app] [namespace]        - Delete deployment"
        echo "  status [app] [namespace]        - Show deployment status"
        echo ""
        echo "Examples:"
        echo "  $0 logs agent-factory-ai default 200"
        echo "  $0 scale agent-factory-ai 3"
        echo "  $0 restart agent-factory-ai"
        echo "  $0 status"
        ;;
esac
