#!/bin/bash

# Generate Kubernetes YAML Files for agent_live_audio_and_text

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

# Load configuration
if [ -f "../config.env" ]; then
    source ../config.env
fi

# Configuration
APP_NAME="${APP_NAME:-agent-audio-text}"
NAMESPACE="${K8S_NAMESPACE:-default}"
REPLICAS="${REPLICAS:-2}"
PORT="${PORT:-8080}"
MEMORY_REQUEST="${MEMORY_REQUEST:-512Mi}"
MEMORY_LIMIT="${MEMORY_LIMIT:-1Gi}"
CPU_REQUEST="${CPU_REQUEST:-500m}"
CPU_LIMIT="${CPU_LIMIT:-1000m}"

mkdir -p ../k8s

print_header "Generating Kubernetes Manifests"

print_info "Configuration:"
echo "  App Name:       $APP_NAME"
echo "  Namespace:      $NAMESPACE"
echo "  Replicas:       $REPLICAS"
echo "  Port:           $PORT"
echo ""

# Generate deployment.yaml
cat > ../k8s/deployment.yaml <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${APP_NAME}
  labels:
    app: ${APP_NAME}
spec:
  replicas: ${REPLICAS}
  selector:
    matchLabels:
      app: ${APP_NAME}
  template:
    metadata:
      labels:
        app: ${APP_NAME}
    spec:
      serviceAccountName: default
      containers:
      - name: ${APP_NAME}
        image: IMAGE_URL_PLACEHOLDER
        ports:
        - containerPort: ${PORT}
          protocol: TCP
        env:
        - name: PORT
          value: "${PORT}"
        - name: PYTHONUNBUFFERED
          value: "1"
        resources:
          requests:
            memory: "${MEMORY_REQUEST}"
            cpu: "${CPU_REQUEST}"
          limits:
            memory: "${MEMORY_LIMIT}"
            cpu: "${CPU_LIMIT}"
        livenessProbe:
          httpGet:
            path: /health
            port: ${PORT}
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: ${PORT}
          initialDelaySeconds: 10
          periodSeconds: 5
EOF

# Generate service.yaml
cat > ../k8s/service.yaml <<EOF
apiVersion: v1
kind: Service
metadata:
  name: ${APP_NAME}
  labels:
    app: ${APP_NAME}
spec:
  type: LoadBalancer
  selector:
    app: ${APP_NAME}
  ports:
  - name: http
    port: 80
    targetPort: ${PORT}
    protocol: TCP
EOF

print_info "✓ Generated: ../k8s/deployment.yaml"
print_info "✓ Generated: ../k8s/service.yaml"
echo ""
print_info "Kubernetes manifests created successfully!"
