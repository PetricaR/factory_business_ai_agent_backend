# GKE Deployment Guide

## Prerequisites

Before running the deployment script, ensure you have:

- ✅ gcloud CLI installed and authenticated
- ✅ Docker installed and running
- ✅ kubectl installed
- ✅ gke-gcloud-auth-plugin installed

## Quick Start

### 1. Set Your Project ID

The only required configuration is your GCP project ID. Set it as an environment variable:

```bash
export GCP_PROJECT_ID="your-actual-project-id"
```

### 2. Run the Deployment Script

```bash
./deploy.sh
```

The script will:

1. Build your Docker image
2. Push it to Google Container Registry (GCR)
3. Deploy to your GKE cluster: `cluter-ai-agents` in `europe-west4`
4. Create a LoadBalancer service to expose your application

### 3. Get the External IP

After deployment, wait a few minutes for the LoadBalancer to provision an external IP:

```bash
kubectl get service agent-factory-ai
```

## Configuration

The script uses these default values (can be overridden with environment variables):

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `GCP_PROJECT_ID` | `your-project-id` | **Required**: Your GCP project ID |
| `CLUSTER_NAME` | `cluter-ai-agents` | Your GKE cluster name |
| `CLUSTER_ZONE` | `europe-west4-a` | Cluster zone |
| `REGION` | `europe-west4` | GCP region |
| `REGISTRY_TYPE` | `gcr` | Registry type (gcr or artifact-registry) |
| `K8S_NAMESPACE` | `default` | Kubernetes namespace |

### Override Examples

```bash
# Use a different namespace
export K8S_NAMESPACE="production"
./deploy.sh

# Use Artifact Registry instead of GCR
export REGISTRY_TYPE="artifact-registry"
export AR_REPOSITORY="my-docker-repo"
./deploy.sh
```

## Kubernetes Manifests

The deployment uses YAML files in the `k8s/` directory:

- **`k8s/deployment.yaml`**: Defines the deployment with 2 replicas, resource limits, and health checks
- **`k8s/service.yaml`**: Creates a LoadBalancer service on port 80

### Customizing the Deployment

Edit `k8s/deployment.yaml` to:

- Add environment variables
- Adjust resource limits
- Change replica count
- Modify health check endpoints

### Adding Secrets

For sensitive data (API keys, credentials), use Kubernetes secrets:

```bash
# Create a secret
kubectl create secret generic agent-secrets \
  --from-literal=API_KEY=your-api-key \
  --namespace=default

# Reference it in k8s/deployment.yaml
env:
- name: API_KEY
  valueFrom:
    secretKeyRef:
      name: agent-secrets
      key: API_KEY
```

## Useful Commands

```bash
# View deployment status
kubectl get deployments

# View pods
kubectl get pods

# Check pod logs
kubectl logs -f <pod-name>

# Scale deployment
kubectl scale deployment agent-factory-ai --replicas=3

# Update deployment manually
kubectl set image deployment/agent-factory-ai agent-factory-ai=gcr.io/PROJECT_ID/agent-factory-ai:new-tag

# Rollback to previous version
kubectl rollout undo deployment/agent-factory-ai

# Delete deployment
kubectl delete deployment agent-factory-ai
kubectl delete service agent-factory-ai
```

## Troubleshooting

### Authentication Issues

```bash
# Re-authenticate with Google Cloud
gcloud auth login

# Configure Docker for GCR
gcloud auth configure-docker
```

### Cluster Access Issues

```bash
# Get cluster credentials
gcloud container clusters get-credentials cluter-ai-agents \
  --zone europe-west4-a \
  --project YOUR_PROJECT_ID
```

### View Deployment Events

```bash
kubectl describe deployment agent-factory-ai
kubectl describe pod <pod-name>
```

### Check Health Status

If pods are not becoming ready, verify:

1. The `/health` endpoint exists in your application
2. Port 8080 is correctly exposed
3. Health check timing is appropriate (adjust `initialDelaySeconds`)

## Notes for Autopilot Clusters

Your cluster is running in **Autopilot mode**, which means:

- Google automatically manages node provisioning and scaling
- Resource requests/limits are required and enforced
- Some node-specific configurations are restricted
- The cluster automatically optimizes for security and efficiency

The deployment manifest is already configured with appropriate resource requests/limits for Autopilot.
