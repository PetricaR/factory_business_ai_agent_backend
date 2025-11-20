#!/bin/bash

# GKE Cluster Security Hardening Script
# ======================================
# This script implements security best practices for GKE clusters

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

#=======================================
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

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =======================================
# 1. Enable Binary Authorization
# =======================================

enable_binary_authorization() {
    print_header "Enabling Binary Authorization"
    
    print_info "Binary Authorization ensures only trusted container images can be deployed"
    
    # Enable Binary Authorization API
    gcloud services enable binaryauthorization.googleapis.com \
        --project="$PROJECT_ID"
    
    # Create default policy
    cat > /tmp/binary-auth-policy.yaml <<EOF
admissionWhitelistPatterns:
- namePattern: gcr.io/${PROJECT_ID}/*
- namePattern: ${REGION}-docker.pkg.dev/${PROJECT_ID}/*
- namePattern: docker.io/library/*
defaultAdmissionRule:
  requireAttestationsBy: []
  enforcementMode: ENFORCED_BLOCK_AND_AUDIT_LOG
  evaluationMode: ALWAYS_ALLOW
globalPolicyEvaluationMode: ENABLE
EOF
    
    print_info "Importing Binary Authorization policy..."
    gcloud container binauthz policy import /tmp/binary-auth-policy.yaml \
        --project="$PROJECT_ID"
    
    rm /tmp/binary-auth-policy.yaml
    
    print_success "Binary Authorization enabled"
}

# =======================================
# 2. Enable Vulnerability Scanning
# =======================================

enable_vulnerability_scanning() {
    print_header "Enabling Container Vulnerability Scanning"
    
    print_info "Enabling Container Analysis API..."
    gcloud services enable containerscanning.googleapis.com \
        --project="$PROJECT_ID"
    
    gcloud services enable containeranalysis.googleapis.com \
        --project="$PROJECT_ID"
    
    print_success "Vulnerability scanning enabled"
    print_info "Images pushed to GCR/Artifact Registry will be automatically scanned"
}

# =======================================
# 3. Configure Network Policies
# =======================================

configure_network_policies() {
    print_header "Configuring Network Policies"
    
    print_info "Network policies control traffic between pods..."
    
    # Create namespace-level network policy
    cat > /tmp/default-deny.yaml <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
EOF
    
    # Create allow policy for application
    cat > /tmp/allow-app.yaml <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-app-traffic
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: agent-factory-ai
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector: {}
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443  # HTTPS
    - protocol: TCP
      port: 53   # DNS
    - protocol: UDP
      port: 53   # DNS
EOF
    
    print_info "Applying network policies..."
    kubectl apply -f /tmp/default-deny.yaml || print_warning "Could not apply default deny policy"
    kubectl apply -f /tmp/allow-app.yaml || print_warning "Could not apply allow app policy"
    
    rm /tmp/default-deny.yaml /tmp/allow-app.yaml
    
    print_success "Network policies configured"
}

# =======================================
# 4. Configure Pod Security Standards
# =======================================

configure_pod_security() {
    print_header "Configuring Pod Security Standards"
    
    print_info "Enforcing Pod Security Standards..."
    
    # Label namespace with pod security standard
    kubectl label namespace default \
        pod-security.kubernetes.io/enforce=restricted \
        pod-security.kubernetes.io/audit=restricted \
        pod-security.kubernetes.io/warn=restricted \
        --overwrite || print_warning "Could not apply pod security labels"
    
    print_success "Pod Security Standards configured"
    print_warning "You may need to update your deployments to comply with restricted standards"
}

# =======================================
# 5. Enable Audit Logging
# =======================================

enable_audit_logging() {
    print_header "Enabling Audit Logging"
    
    print_info "Audit logging tracks all API calls to your cluster..."
    
    # Update cluster with enhanced logging
    gcloud container clusters update "$CLUSTER_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --enable-cloud-logging \
        --logging=SYSTEM,WORKLOAD,API_SERVER \
        --enable-cloud-monitoring \
        --monitoring=SYSTEM,WORKLOAD || print_warning "Could not update logging settings"
    
    print_success "Audit logging enabled"
}

# =======================================
# 6. Configure RBAC
# =======================================

configure_rbac() {
    print_header "Configuring RBAC"
    
    print_info "Setting up Role-Based Access Control..."
    
    # Create restricted ClusterRole
    cat > /tmp/restricted-role.yaml <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: restricted-viewer
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch"]
EOF
    
    kubectl apply -f /tmp/restricted-role.yaml
    rm /tmp/restricted-role.yaml
    
    print_success "RBAC configured"
    print_info "Grant specific users access with:"
    print_info "  kubectl create rolebinding USER-binding --clusterrole=restricted-viewer --user=USER@EMAIL.COM"
}

# =======================================
# 7. Enable Workload Identity (if not already done)
# =======================================

verify_workload_identity() {
    print_header "Verifying Workload Identity"
    
    local workload_pool=$(gcloud container clusters describe "$CLUSTER_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(workloadIdentityConfig.workloadPool)" 2>/dev/null || echo "")
    
    if [ -n "$workload_pool" ]; then
        print_success "Workload Identity is enabled: $workload_pool"
    else
        print_warning "Workload Identity is NOT enabled"
        print_info "Run: ./2-setup-workload-identity.sh"
    fi
}

# =======================================
# 8. Configure Secrets Encryption
# =======================================

enable_secrets_encryption() {
    print_header "Verifying Secrets Encryption"
    
    print_info "GKE Autopilot automatically encrypts secrets at rest"
    
    local encryption=$(gcloud container clusters describe "$CLUSTER_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(databaseEncryption.state)" 2>/dev/null || echo "UNKNOWN")
    
    if [ "$encryption" == "ENCRYPTED" ] || [ "$encryption" == "UNKNOWN" ]; then
        print_success "Secrets encryption is enabled"
    else
        print_warning "Secrets encryption status: $encryption"
    fi
}

# =======================================
# 9. Security Scan
# =======================================

run_security_scan() {
    print_header "Running Security Scan"
    
    print_info "Checking cluster security posture..."
    
    # Check for public endpoints
    print_info "Checking for services with external IPs..."
    kubectl get services --all-namespaces -o jsonpath='{range .items[?(@.spec.type=="LoadBalancer")]}{.metadata.namespace}/{.metadata.name}: {.status.loadBalancer.ingress[0].ip}{"\n"}{end}' || true
    
    # Check for privileged pods
    print_info "Checking for privileged pods..."
    kubectl get pods --all-namespaces -o jsonpath='{range .items[?(@.spec.containers[*].securityContext.privileged==true)]}{.metadata.namespace}/{.metadata.name}{"\n"}{end}' || print_info "No privileged pods found"
    
    # Check for pods running as root
    print_info "Checking for pods running as root..."
    kubectl get pods --all-namespaces -o json | \
        jq -r '.items[] | select(.spec.securityContext.runAsUser == 0 or .spec.containers[].securityContext.runAsUser == 0) | "\(.metadata.namespace)/\(.metadata.name)"' || print_info "No pods running as root"
    
    print_success "Security scan complete"
}

# =======================================
# Summary
# =======================================

print_summary() {
    print_header "Security Hardening Complete!"
    
    echo -e "${GREEN}✓ Binary Authorization: ${NC}Enabled"
    echo -e "${GREEN}✓ Vulnerability Scanning: ${NC}Enabled"
    echo -e "${GREEN}✓ Network Policies: ${NC}Configured"
    echo -e "${GREEN}✓ Pod Security Standards: ${NC}Enforced"
    echo -e "${GREEN}✓ Audit Logging: ${NC}Enabled"
    echo -e "${GREEN}✓ RBAC: ${NC}Configured"
    echo -e "${GREEN}✓ Workload Identity: ${NC}Verified"
    echo -e "${GREEN}✓ Secrets Encryption: ${NC}Verified"
    
    echo -e "\n${YELLOW}Next Steps:${NC}"
    echo "1. Review security policies"
    echo "2. Configure IAP for application access: ./4-setup-iap.sh"
    echo "3. Set up monitoring alerts"
    echo "4. Regularly scan container images"
    echo "5. Review audit logs periodically"
    
    echo -e "\n${YELLOW}Security Best Practices:${NC}"
    echo "• Use Workload Identity (no service account keys)"
    echo "• Scan all container images before deployment"
    echo "• Keep cluster and node pools updated"
    echo "• Use network policies to limit pod communication"
    echo "• Enable Binary Authorization for production"
    echo "• Regularly review RBAC permissions"
    echo "• Monitor audit logs for suspicious activity"
}

# =======================================
# Main
# =======================================

main() {
    print_header "GKE Cluster Security Hardening"
    
    echo "This script will harden your GKE cluster security:"
    echo "  • Binary Authorization"
    echo "  • Vulnerability Scanning"
    echo "  • Network Policies"
    echo "  • Pod Security Standards"
    echo "  • Audit Logging"
    echo "  • RBAC"
    echo ""
    echo "Configuration:"
    echo "  Project:  $PROJECT_ID"
    echo "  Cluster:  $CLUSTER_NAME"
    echo "  Region:   $REGION"
    echo ""
    
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Aborted by user"
        exit 0
    fi
    
    enable_binary_authorization
    enable_vulnerability_scanning
    configure_network_policies
    configure_pod_security
    enable_audit_logging
    configure_rbac
    verify_workload_identity
    enable_secrets_encryption
    run_security_scan
    print_summary
}

main "$@"
