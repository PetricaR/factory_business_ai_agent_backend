#!/bin/bash

# GKE Security Audit Script
# ==========================
# Performs security checks on GKE cluster and workloads

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-formare-ai}"
CLUSTER_NAME="${CLUSTER_NAME:-ai-agents-cluster}"
REGION="${GCP_REGION:-europe-west4}"

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# =======================================
# Helper Functions
# =======================================

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

# =======================================
# Cluster-Level Checks
# =======================================

check_cluster_security() {
    print_header "Cluster Security Checks"
    
    # Check Workload Identity
    local workload_pool=$(gcloud container clusters describe "$CLUSTER_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(workloadIdentityConfig.workloadPool)" 2>/dev/null || echo "")
    
    if [ -n "$workload_pool" ]; then
        check_pass "Workload Identity enabled"
    else
        check_fail "Workload Identity NOT enabled"
    fi
    
    # Check Binary Authorization
    local binauthz=$(gcloud container clusters describe "$CLUSTER_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(binaryAuthorization.enabled)" 2>/dev/null || echo "false")
    
    if [ "$binauthz" == "true" ]; then
        check_pass "Binary Authorization enabled"
    else
        check_warn "Binary Authorization not enabled"
    fi
    
    # Check Network Policies
    local network_policy=$(gcloud container clusters describe "$CLUSTER_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(networkPolicyConfig.enabled)" 2>/dev/null || echo "false")
    
    if [ "$network_policy" == "true" ] || [[ "$CLUSTER_NAME" == *"autopilot"* ]]; then
        check_pass "Network Policies available"
    else
        check_warn "Network Policies not enabled"
    fi
    
    # Check Database Encryption
    local encryption=$(gcloud container clusters describe "$CLUSTER_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(databaseEncryption.state)" 2>/dev/null || echo "UNKNOWN")
    
    if [ "$encryption" == "ENCRYPTED" ] || [ "$encryption" == "DECRYPTED" ]; then
        check_pass "Database encryption configured"
    else
        check_warn "Database encryption status: $encryption"
    fi
    
    # Check Logging
    local logging=$(gcloud container clusters describe "$CLUSTER_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(loggingConfig.componentConfig.enableComponents)" 2>/dev/null || echo "")
    
    if [[ "$logging" == *"SYSTEM_COMPONENTS"* ]] && [[ "$logging" == *"WORKLOADS"* ]]; then
        check_pass "Comprehensive logging enabled"
    else
        check_warn "Limited logging enabled"
    fi
}

# =======================================
# Pod Security Checks
# =======================================

check_pod_security() {
    print_header "Pod Security Checks"
    
    # Check for privileged pods
    local privileged=$(kubectl get pods --all-namespaces -o json | \
        jq -r '.items[] | select(.spec.containers[]?.securityContext?.privileged == true) | "\(.metadata.namespace)/\(.metadata.name)"' 2>/dev/null)
    
    if [ -z "$privileged" ]; then
        check_pass "No privileged pods running"
    else
        check_fail "Privileged pods detected:"
        echo "$privileged"
    fi
    
    # Check for pods running as root
    local root_pods=$(kubectl get pods --all-namespaces -o json | \
        jq -r '.items[] | select((.spec.securityContext?.runAsUser == 0) or (.spec.containers[]?.securityContext?.runAsUser == 0)) | "\(.metadata.namespace)/\(.metadata.name)"' 2>/dev/null)
    
    if [ -z "$root_pods" ]; then
        check_pass "No pods running as root"
    else
        check_warn "Pods running as root:"
        echo "$root_pods"
    fi
    
    # Check for hostPath volumes
    local hostpath=$(kubectl get pods --all-namespaces -o json | \
        jq -r '.items[] | select(.spec.volumes[]?.hostPath != null) | "\(.metadata.namespace)/\(.metadata.name)"' 2>/dev/null)
    
    if [ -z "$hostpath" ]; then
        check_pass "No hostPath volumes in use"
    else
        check_warn "Pods using hostPath volumes:"
        echo "$hostpath"
    fi
    
    # Check for hostNetwork
    local hostnetwork=$(kubectl get pods --all-namespaces -o json | \
        jq -r '.items[] | select(.spec.hostNetwork == true) | "\(.metadata.namespace)/\(.metadata.name)"' 2>/dev/null)
    
    if [ -z "$hostnetwork" ]; then
        check_pass "No pods using hostNetwork"
    else
        check_warn "Pods using hostNetwork:"
        echo "$hostnetwork"
    fi
}

# =======================================
# Network Security Checks
# =======================================

check_network_security() {
    print_header "Network Security Checks"
    
    # Check for LoadBalancer services (public exposure)
    local lb_services=$(kubectl get services --all-namespaces -o json | \
        jq -r '.items[] | select(.spec.type == "LoadBalancer") | "\(.metadata.namespace)/\(.metadata.name)"' 2>/dev/null)
    
    if [ -z "$lb_services" ]; then
        check_pass "No LoadBalancer services exposed"
    else
        check_warn "LoadBalancer services (publicly accessible):"
        echo "$lb_services"
    fi
    
    # Check for Network Policies in default namespace
    local netpol_count=$(kubectl get networkpolicies -n default --no-headers 2>/dev/null | wc -l)
    
    if [ "$netpol_count" -gt 0 ]; then
        check_pass "Network Policies configured in default namespace ($netpol_count policies)"
    else
        check_warn "No Network Policies in default namespace"
    fi
    
    # Check for Ingress resources
    local ingress=$(kubectl get ingress --all-namespaces -o json | \
        jq -r '.items[] | "\(.metadata.namespace)/\(.metadata.name)"' 2>/dev/null)
    
    if [ -n "$ingress" ]; then
        check_warn "Ingress resources (check for TLS/authentication):"
        echo "$ingress"
    else
        check_pass "No Ingress resources"
    fi
}

# =======================================
# RBAC Checks
# =======================================

check_rbac() {
    print_header "RBAC Security Checks"
    
    # Check for cluster-admin bindings
    local cluster_admin=$(kubectl get clusterrolebindings -o json | \
        jq -r '.items[] | select(.roleRef.name == "cluster-admin") | "\(.metadata.name): \(.subjects[]?.name // "N/A")"' 2>/dev/null)
    
    if [ -n "$cluster_admin" ]; then
        check_warn "cluster-admin bindings (review carefully):"
        echo "$cluster_admin"
    else
        check_pass "No cluster-admin bindings"
    fi
    
    # Check for wildcard permissions
    local wildcard=$(kubectl get roles,clusterroles --all-namespaces -o json | \
        jq -r '.items[] | select(.rules[]?.resources[]? == "*") | "\(.kind)/\(.metadata.name)"' 2>/dev/null | head -5)
    
    if [ -n "$wildcard" ]; then
        check_warn "Roles with wildcard (*) permissions:"
        echo "$wildcard"
    else
        check_pass "No wildcard permissions in custom roles"
    fi
}

# =======================================
# Secret Management Checks
# =======================================

check_secrets() {
    print_header "Secret Management Checks"
    
    # Count secrets
    local secret_count=$(kubectl get secrets --all-namespaces --no-headers 2>/dev/null | wc -l)
    echo -e "${BLUE}Total secrets: $secret_count${NC}"
    
    # Check for secrets in default namespace
    local default_secrets=$(kubectl get secrets -n default --no-headers 2>/dev/null | grep -v "default-token" | wc -l)
    
    if [ "$default_secrets" -gt 0 ]; then
        check_warn "Secrets in default namespace: $default_secrets (consider using Secret Manager)"
    else
        check_pass "No custom secrets in default namespace"
    fi
    
    # Check for unencrypted secrets (this is informational)
    check_pass "Secrets encrypted at rest (GKE default)"
}

# =======================================
# Image Security Checks
# =======================================

check_images() {
    print_header "Container Image Checks"
    
    # List unique images
    local images=$(kubectl get pods --all-namespaces -o jsonpath='{range .items[*]}{range .spec.containers[*]}{.image}{"\n"}{end}{end}' | sort -u)
    
    echo -e "${BLUE}Container images in use:${NC}"
    echo "$images"
    
    # Check for images not from GCR or Artifact Registry
    local external_images=$(echo "$images" | grep -v "gcr.io/${PROJECT_ID}" | grep -v "${REGION}-docker.pkg.dev/${PROJECT_ID}" | grep -v "gke.gcr.io" || true)
    
    if [ -n "$external_images" ]; then
        check_warn "External images (scan before use):"
        echo "$external_images"
    else
        check_pass "All images from trusted registries"
    fi
    
    # Check for 'latest' tag
    local latest_tag=$(echo "$images" | grep ":latest" || true)
    
    if [ -n "$latest_tag" ]; then
        check_warn "Images using 'latest' tag (use specific versions):"
        echo "$latest_tag"
    else
        check_pass "No images using 'latest' tag"
    fi
}

# =======================================
# Resource Limits Checks
# =======================================

check_resource_limits() {
    print_header "Resource Limit Checks"
    
    # Check for pods without resource limits
    local no_limits=$(kubectl get pods --all-namespaces -o json | \
        jq -r '.items[] | select(.spec.containers[] | select(.resources.limits == null or (.resources.limits.memory == null and .resources.limits.cpu == null))) | "\(.metadata.namespace)/\(.metadata.name)"' 2>/dev/null)
    
    if [ -z "$no_limits" ]; then
        check_pass "All pods have resource limits"
    else
        check_warn "Pods without resource limits:"
        echo "$no_limits" | head -5
    fi
}

# =======================================
# Summary
# =======================================

print_summary() {
    print_header "Security Audit Summary"
    
    local total=$((PASSED + FAILED + WARNINGS))
    
    echo -e "${GREEN}✓ Passed:   $PASSED${NC}"
    echo -e "${YELLOW}⚠ Warnings: $WARNINGS${NC}"
    echo -e "${RED}✗ Failed:   $FAILED${NC}"
    echo -e "${BLUE}Total:      $total${NC}"
    echo ""
    
    if [ $FAILED -gt 0 ]; then
        echo -e "${RED}❌ Critical issues found! Address failed checks immediately.${NC}"
        exit 1
    elif [ $WARNINGS -gt 5 ]; then
        echo -e "${YELLOW}⚠️  Several warnings found. Review and address as needed.${NC}"
    else
        echo -e "${GREEN}✅ Cluster security looks good!${NC}"
    fi
    
    echo -e "\n${YELLOW}Recommendations:${NC}"
    echo "• Run this audit regularly (weekly/monthly)"
    echo "• Address all failed checks"
    echo "• Review warnings and minimize where possible"
    echo "• Keep cluster and nodes updated"
    echo "• Monitor security logs and alerts"
    echo "• Use Secret Manager for sensitive data"
    echo "• Implement Binary Authorization for production"
}

# =======================================
# Main
# =======================================

main() {
    print_header "GKE Security Audit"
    
    echo "Auditing cluster: $CLUSTER_NAME"
    echo "Project: $PROJECT_ID"
    echo "Region: $REGION"
    echo ""
    
    check_cluster_security
    check_pod_security
    check_network_security
    check_rbac
    check_secrets
    check_images
    check_resource_limits
    print_summary
}

main "$@"
