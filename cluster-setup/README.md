# GKE Cluster Setup

## Overview

This directory contains scripts for **one-time infrastructure provisioning** of a GKE Autopilot cluster. These scripts set up the foundational infrastructure that can be shared across multiple application deployments.

## 📋 What This Sets Up

- ✅ GKE Autopilot cluster
- ✅ Workload Identity configuration
- ✅ Service account with Vertex AI permissions
- ✅ Cloud logging and monitoring
- ✅ (Optional) Identity-Aware Proxy (IAP)

## 🚀 Quick Start

### Prerequisites

- Google Cloud SDK (`gcloud`)
- Docker Desktop
- Active GCP project with billing enabled

### Step 1: Configure

Edit `config.env` with your GCP project settings:

```bash
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="europe-west4"
export CLUSTER_NAME="ai-agents-cluster"
```

Load the configuration:

```bash
source config.env
```

### Step 2: Create Cluster

Create the GKE Autopilot cluster (takes 5-10 minutes):

```bash
cd scripts
chmod +x *.sh
./1-create-cluster.sh
```

This script will:

- Enable required GCP APIs
- Create a regional Autopilot cluster
- Configure Workload Identity
- Set up logging and monitoring

### Step 3: Setup Workload Identity

Configure authentication for your applications (takes 2-3 minutes):

```bash
./2-setup-workload-identity.sh
```

This script will:

- Create a GCP service account
- Grant Vertex AI permissions (for Gemini models)
- Enable Workload Identity binding
- Annotate Kubernetes service account

### Step 3: Security Hardening 🔒

Harden your cluster security (takes 3-5 minutes):

```bash
./3-security-hardening.sh
```

This script will:

- Enable Binary Authorization
- Configure Vulnerability Scanning
- Setup Network Policies
- Enforce Pod Security Standards
- Enable Audit Logging
- Configure RBAC
- Verify encryption

### Step 4: Security Audit

Run a security audit to ensure best practices:

```bash
./security-audit.sh
```

### Step 5 (Optional): Setup IAP

If you need Identity-Aware Proxy for secure access:

```bash
./4-setup-iap.sh
```

## 📝 Scripts Reference

| Script | Purpose | Duration | Frequency |
|--------|---------|----------|-----------|
| `1-create-cluster.sh` | Create GKE cluster | 5-10 min | **Once** |
| `2-setup-workload-identity.sh` | Configure authentication | 2-3 min | **Once** (or per app) |
| `3-security-hardening.sh` | Harden cluster security | 3-5 min | **Once** |
| `security-audit.sh` | Run security audit | 1-2 min | **Weekly/Monthly** |
| `4-setup-iap.sh` | Setup IAP (optional) | 3-5 min | **Once** |

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GCP_PROJECT_ID` | `formare-ai` | Your GCP project ID |
| `GCP_REGION` | `europe-west4` | GCP region for cluster |
| `CLUSTER_NAME` | `ai-agents-cluster` | Name of GKE cluster |
| `APP_NAME` | `agent-factory-ai` | Application name (for SA) |
| `K8S_NAMESPACE` | `default` | Kubernetes namespace |

### Customizing the Cluster

You can customize cluster settings in `1-create-cluster.sh`:

```bash
# Change region
export GCP_REGION="us-central1"

# Change cluster name
export CLUSTER_NAME="my-cluster"
```

## ✅ Verification

After running the setup scripts, verify everything is configured correctly:

```bash
# Check cluster status
gcloud container clusters describe $CLUSTER_NAME \
  --region=$GCP_REGION \
  --project=$GCP_PROJECT_ID

# List nodes
kubectl get nodes

# Verify service account
kubectl get serviceaccount -n $K8S_NAMESPACE
```

## 📚 Next Steps

After completing cluster setup:

1. Navigate to `../cluster-deployment`
2. Configure your application settings
3. Deploy your application using the deployment scripts

See [../cluster-deployment/README.md](../cluster-deployment/README.md) for deployment instructions.

## 🔍 Troubleshooting

### API Not Enabled Error

```bash
# Enable required APIs manually
gcloud services enable container.googleapis.com
gcloud services enable compute.googleapis.com
gcloud services enable aiplatform.googleapis.com
```

### Cluster Already Exists

If the cluster already exists, the script will ask if you want to use it. Choose:

- **Yes** to use the existing cluster
- **No** to abort and choose a different name

### Permission Denied

Ensure your GCP account has the following roles:

- `roles/container.admin` - Create and manage GKE clusters
- `roles/iam.serviceAccountAdmin` - Manage service accounts
- `roles/resourcemanager.projectIamAdmin` - Grant IAM permissions

## 🧹 Clean Up

To delete the cluster and all resources:

```bash
# Delete the cluster (WARNING: Irreversible!)
gcloud container clusters delete $CLUSTER_NAME \
  --region=$GCP_REGION \
  --project=$GCP_PROJECT_ID

# Delete the service account
gcloud iam service-accounts delete \
  ${APP_NAME}-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com
```

## 📖 Additional Resources

- [GKE Autopilot Overview](https://cloud.google.com/kubernetes-engine/docs/concepts/autopilot-overview)
- [Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)

---

**Note**: These scripts are designed for **one-time setup**. Once your cluster is configured, use the `cluster-deployment` scripts for deploying applications.
