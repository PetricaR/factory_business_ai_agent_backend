# Application Deployment to GKE

## Overview

This directory contains scripts for **deploying applications** to an existing GKE cluster. These scripts can be run repeatedly to deploy new versions or multiple applications to the same cluster.

## 📋 Prerequisites

Before deploying, ensure you have:

- ✅ A running GKE cluster (see [../cluster-setup/README.md](../cluster-setup/README.md))
- ✅ Workload Identity configured
- ✅ Docker installed and running
- ✅ Access to the cluster via `kubectl`

## 🚀 Quick Start

### Step 1: Configure

Edit `config.env` with your application settings:

```bash
export GCP_PROJECT_ID="your-project-id"
export APP_NAME="agent-factory-ai"
export CLUSTER_NAME="ai-agents-cluster"
```

Load the configuration:

```bash
source config.env
```

### Step 2: Deploy Application

Deploy your application with a single command:

```bash
cd scripts
chmod +x *.sh
./deploy-application.sh
```

This script will:

1. Build Docker image for `linux/amd64`
2. Push image to Google Container Registry
3. Deploy to Kubernetes
4. Create LoadBalancer service
5. Wait for deployment to complete

### Step 3: Access Your Application

Get the external IP address:

```bash
./utils.sh ip
```

Access your application:

- Main interface: `http://YOUR_EXTERNAL_IP`
- Health check: `http://YOUR_EXTERNAL_IP/health`
- API docs: `http://YOUR_EXTERNAL_IP/docs`

## 📝 Scripts Reference

| Script | Purpose | Duration |
|--------|---------|----------|
| `deploy-application.sh` | Full deployment pipeline | 5-7 min |
| `0-generate-k8s-manifests.sh` | Generate K8s manifests | Instant |
| `utils.sh` | Utility commands | Instant |

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GCP_PROJECT_ID` | `formare-ai` | Your GCP project ID |
| `GCP_REGION` | `europe-west4` | GCP region |
| `CLUSTER_NAME` | `ai-agents-cluster` | Target cluster name |
| `APP_NAME` | `agent-factory-ai` | Application name |
| `K8S_NAMESPACE` | `default` | Kubernetes namespace |
| `REPLICAS` | `2` | Number of pod replicas |
| `PORT` | `8080` | Application port |
| `MEMORY_REQUEST` | `512Mi` | Memory request |
| `MEMORY_LIMIT` | `1Gi` | Memory limit |
| `CPU_REQUEST` | `500m` | CPU request |
| `CPU_LIMIT` | `1000m` | CPU limit |
| `REGISTRY_TYPE` | `gcr` | Registry type (gcr/artifact-registry) |

### Customizing Resources

Edit `config.env` to adjust resources:

```bash
# Scale to more replicas
export REPLICAS="5"

# Increase memory
export MEMORY_REQUEST="1Gi"
export MEMORY_LIMIT="2Gi"

# Increase CPU
export CPU_REQUEST="1000m"
export CPU_LIMIT="2000m"
```

Or directly edit `k8s/deployment.yaml`.

## 🛠️ Utility Commands

The `utils.sh` script provides helpful commands:

### View Logs

```bash
# Last 100 lines
./utils.sh logs

# Last 200 lines
./utils.sh logs agent-factory-ai default 200
```

### Scale Deployment

```bash
# Scale to 5 replicas
./utils.sh scale agent-factory-ai 5
```

### Restart Deployment

```bash
# Rolling restart
./utils.sh restart
```

### Get External IP

```bash
./utils.sh ip
```

### Check Status

```bash
./utils.sh status
```

### Delete Deployment

```bash
# WARNING: This deletes the deployment
./utils.sh delete
```

## 📦 Kubernetes Manifests

### deployment.yaml

Defines the application deployment:

- Number of replicas
- Container image
- Resource limits
- Health checks
- Environment variables

### service.yaml

Defines the LoadBalancer service:

- External IP allocation
- Port mapping
- Service type

## 🔄 Deployment Workflow

### First-Time Deployment

If this is your first deployment:

```bash
# 1. Setup cluster (one-time)
cd ../cluster-setup/scripts
./1-create-cluster.sh
./2-setup-workload-identity.sh

# 2. Deploy application
cd ../../cluster-deployment/scripts
./deploy-application.sh
```

### Update Deployment

To deploy a new version:

```bash
# Simply re-run the deployment script
./deploy-application.sh
```

The script will:

- Build a new Docker image with timestamp tag
- Push to registry
- Update Kubernetes deployment
- Perform rolling update (zero downtime)

### Deploy Multiple Applications

To deploy multiple apps to the same cluster:

```bash
# Deploy first app
export APP_NAME="app-one"
./deploy-application.sh

# Deploy second app
export APP_NAME="app-two"
./deploy-application.sh
```

## 🔍 Troubleshooting

### Pods in CrashLoopBackOff

Check logs:

```bash
kubectl get pods
kubectl logs POD_NAME
```

Common causes:

- Missing environment variables
- Wrong platform (must be `linux/amd64`)
- Port conflicts

### External IP Shows \<pending\>

LoadBalancer provisioning takes 2-5 minutes. Check status:

```bash
kubectl get service $APP_NAME
```

If still pending after 10 minutes:

```bash
kubectl describe service $APP_NAME
```

### Permission Denied Error

```bash
# Error: 403 PERMISSION_DENIED
# Solution: Re-run workload identity setup
cd ../cluster-setup/scripts
./2-setup-workload-identity.sh

# Then restart deployment
cd ../../cluster-deployment/scripts
./utils.sh restart
```

### Docker Build Fails

Ensure Docker is running:

```bash
docker ps
```

Check platform is correct:

```bash
# Should be linux/amd64 for GKE
docker build --platform=linux/amd64 ...
```

## 📊 Monitoring

### View Deployment Status

```bash
kubectl get deployments
kubectl describe deployment $APP_NAME
```

### View Pod Status

```bash
kubectl get pods
kubectl describe pod POD_NAME
```

### View Service Status

```bash
kubectl get services
kubectl describe service $APP_NAME
```

### View Logs

```bash
# All pods
kubectl logs -l app=$APP_NAME --tail=100

# Specific pod
kubectl logs POD_NAME --tail=100 -f
```

## 🎯 Best Practices

### 1. Use Tagged Images

Always tag your images with versions:

```bash
# The script automatically tags with timestamp
# e.g., gcr.io/project/app:20231120-143052
```

### 2. Test Locally First

Before deploying to GKE, test locally:

```bash
# Build and run locally
docker build -t test-app .
docker run -p 8080:8080 test-app
```

### 3. Use Rolling Updates

The deployment uses rolling updates by default:

- Zero downtime
- Gradual rollout
- Easy rollback

### 4. Monitor Resource Usage

Check resource usage:

```bash
kubectl top pods
kubectl top nodes
```

### 5. Set Up Health Checks

Ensure your app has health endpoints:

- `/health` - Liveness probe
- `/ready` - Readiness probe

## 🔄 Rollback

If a deployment fails, rollback to previous version:

```bash
# View rollout history
kubectl rollout history deployment/$APP_NAME

# Rollback to previous version
kubectl rollout undo deployment/$APP_NAME

# Rollback to specific revision
kubectl rollout undo deployment/$APP_NAME --to-revision=2
```

## 📚 Additional Resources

- [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [GKE Best Practices](https://cloud.google.com/kubernetes-engine/docs/best-practices)
- [Docker Multi-Platform Builds](https://docs.docker.com/build/building/multi-platform/)

---

**Note**: This directory is for **application deployment only**. For cluster setup, see [../cluster-setup/](../cluster-setup/).
