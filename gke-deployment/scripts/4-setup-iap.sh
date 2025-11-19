#!/bin/bash

# Identity-Aware Proxy (IAP) Setup Script
# ========================================
# Secures your application with Google authentication
# Only allows access to specific email addresses

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
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
APP_NAME="${APP_NAME:-agent-factory-ai}"
NAMESPACE="${K8S_NAMESPACE:-default}"
REGION="${GCP_REGION:-europe-west4}"

# Allowed emails (edit this list)
ALLOWED_EMAILS=(
    "petrica.radan@formare.ai"
    # Add more emails here:
    # "user2@formare.ai"
    # "user3@formare.ai"
)

print_header "IAP Security Setup"

echo "This script will:"
echo "  1. Enable IAP API"
echo "  2. Create necessary Kubernetes resources"
echo "  3. Grant access to specific email addresses"
echo ""
echo "Allowed emails:"
for email in "${ALLOWED_EMAILS[@]}"; do
    echo "  - $email"
done
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Aborted"
    exit 0
fi

# Step 1: Enable IAP API
print_header "Step 1: Enable IAP API"
gcloud services enable iap.googleapis.com --project=$PROJECT_ID
gcloud services enable compute.googleapis.com --project=$PROJECT_ID
print_info "✓ APIs enabled"

# Step 2: Manual OAuth Setup Required
print_header "Step 2: OAuth Consent Screen (Manual)"
print_warning "You need to complete these steps manually in the Google Cloud Console:"
echo ""
echo "1. Create OAuth Consent Screen:"
echo "   https://console.cloud.google.com/apis/credentials/consent?project=$PROJECT_ID"
echo ""
echo "   - Choose 'Internal' (for @formare.ai) or 'External'"
echo "   - App name: Agent Factory AI"
echo "   - User support email: ${ALLOWED_EMAILS[0]}"
echo "   - Authorized domains: Add your domain if using custom domain"
echo ""
echo "2. Create OAuth 2.0 Credentials:"
echo "   https://console.cloud.google.com/apis/credentials?project=$PROJECT_ID"
echo ""
echo "   - Click 'Create Credentials' → 'OAuth client ID'"
echo "   - Application type: Web application"
echo "   - Name: IAP Client"
echo "   - Authorized redirect URIs: Will be auto-configured by IAP"
echo ""
print_warning "Complete these steps, then press Enter to continue..."
read

# Step 3: Get OAuth credentials
print_header "Step 3: OAuth Credentials"
echo "Enter your OAuth Client ID:"
read CLIENT_ID
echo "Enter your OAuth Client Secret:"
read -s CLIENT_SECRET
echo ""

# Create Kubernetes secret
print_info "Creating Kubernetes secret..."
kubectl create secret generic oauth-client-credentials \
    --from-literal=client_id=$CLIENT_ID \
    --from-literal=client_secret=$CLIENT_SECRET \
    -n $NAMESPACE \
    --dry-run=client -o yaml | kubectl apply -f -
print_info "✓ OAuth secret created"

# Step 4: Reserve Static IP
print_header "Step 4: Reserve Static IP"
print_info "Reserving static IP address..."
if ! gcloud compute addresses describe ${APP_NAME}-ip --global --project=$PROJECT_ID &> /dev/null; then
    gcloud compute addresses create ${APP_NAME}-ip --global --project=$PROJECT_ID
    print_info "✓ Static IP reserved"
else
    print_info "✓ Static IP already exists"
fi

STATIC_IP=$(gcloud compute addresses describe ${APP_NAME}-ip --global --format="value(address)" --project=$PROJECT_ID)
print_info "Static IP: $STATIC_IP"

# Step 5: Create Kubernetes Resources
print_header "Step 5: Create Kubernetes Resources"

# Backend Config
print_info "Creating BackendConfig..."
cat > /tmp/backend-config.yaml <<EOF
apiVersion: cloud.google.com/v1
kind: BackendConfig
metadata:
  name: ${APP_NAME}-backend-config
  namespace: $NAMESPACE
spec:
  iap:
    enabled: true
    oauthclientCredentials:
      secretName: oauth-client-credentials
  healthCheck:
    checkIntervalSec: 10
    port: 8080
    type: HTTP
    requestPath: /health
EOF

kubectl apply -f /tmp/backend-config.yaml
print_info "✓ BackendConfig created"

# Update Service
print_info "Updating Service to ClusterIP..."
cat > /tmp/service-iap.yaml <<EOF
apiVersion: v1
kind: Service
metadata:
  name: $APP_NAME
  namespace: $NAMESPACE
  annotations:
    cloud.google.com/backend-config: '{"default": "${APP_NAME}-backend-config"}'
    cloud.google.com/neg: '{"ingress": true}'
spec:
  type: ClusterIP
  selector:
    app: $APP_NAME
  ports:
  - name: http
    port: 80
    targetPort: 8080
    protocol: TCP
EOF

kubectl apply -f /tmp/service-iap.yaml
print_info "✓ Service updated"

# Create Ingress
print_info "Creating Ingress..."
cat > /tmp/ingress-iap.yaml <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ${APP_NAME}-ingress
  namespace: $NAMESPACE
  annotations:
    kubernetes.io/ingress.class: "gce"
    kubernetes.io/ingress.global-static-ip-name: "${APP_NAME}-ip"
    networking.gke.io/managed-certificates: "${APP_NAME}-cert"
spec:
  defaultBackend:
    service:
      name: $APP_NAME
      port:
        number: 80
EOF

kubectl apply -f /tmp/ingress-iap.yaml
print_info "✓ Ingress created"

# Wait for Ingress
print_info "Waiting for Ingress to be ready (this may take 5-10 minutes)..."
kubectl wait --for=condition=Available ingress/${APP_NAME}-ingress -n $NAMESPACE --timeout=600s || true

# Step 6: Grant Access to Users
print_header "Step 6: Grant Access to Users"

# Get backend service name
sleep 30  # Wait for backend service to be created
BACKEND_SERVICE=$(gcloud compute backend-services list --format="value(name)" --filter="name~${APP_NAME}" --project=$PROJECT_ID | head -n 1)

if [ -z "$BACKEND_SERVICE" ]; then
    print_error "Backend service not found yet. It may still be creating."
    print_warning "Run this command manually after a few minutes:"
    echo ""
    for email in "${ALLOWED_EMAILS[@]}"; do
        echo "gcloud iap web add-iam-policy-binding \\"
        echo "  --resource-type=backend-services \\"
        echo "  --service=BACKEND_SERVICE_NAME \\"
        echo "  --member='user:$email' \\"
        echo "  --role='roles/iap.httpsResourceAccessor'"
        echo ""
    done
else
    print_info "Backend service: $BACKEND_SERVICE"
    print_info "Granting access to users..."
    
    for email in "${ALLOWED_EMAILS[@]}"; do
        print_info "Granting access to: $email"
        gcloud iap web add-iam-policy-binding \
            --resource-type=backend-services \
            --service=$BACKEND_SERVICE \
            --member="user:$email" \
            --role="roles/iap.httpsResourceAccessor" \
            --project=$PROJECT_ID
    done
    
    print_info "✓ Access granted to all users"
fi

# Summary
print_header "Setup Complete!"
echo -e "${GREEN}✓ IAP is now enabled${NC}"
echo -e "${GREEN}✓ Static IP: ${NC}$STATIC_IP"
echo ""
echo "Authorized users:"
for email in "${ALLOWED_EMAILS[@]}"; do
    echo "  ✓ $email"
done
echo ""
print_info "Your application will be accessible at: http://$STATIC_IP"
print_info "Users will be prompted to sign in with Google"
print_info "Only authorized emails can access the application"
echo ""
print_warning "Note: It may take 5-10 minutes for IAP to be fully active"
echo ""
echo "To add more users:"
echo "  gcloud iap web add-iam-policy-binding \\"
echo "    --resource-type=backend-services \\"
echo "    --service=$BACKEND_SERVICE \\"
echo "    --member='user:new.user@formare.ai' \\"
echo "    --role='roles/iap.httpsResourceAccessor'"
