# GKE Internal Deployment

## Overview

This directory contains scripts for deploying applications to GKE with **internal network access only**. This uses an **Internal LoadBalancer** which provides a **private IP address** that's accessible from:

- ✅ Your internal network / VPN
- ✅ Other GCP resources in the same VPC
- ✅ On-premises networks connected via Cloud VPN or Interconnect
- ❌ **NOT** from the public internet

## 🔒 Internal vs Public Deployment

| Feature | gke-deployment (Public) | gke-internal-deployment (This) |
|---------|------------------------|--------------------------------|
| **Service Type** | LoadBalancer (Public) | LoadBalancer (Internal) |
| **IP Address** | Public External IP | Private Internal IP |
| **Internet Access** | ✅ Yes | ❌ No |
| **VPN/Internal Network** | ✅ Yes | ✅ Yes |
| **Access Method** | Direct HTTP via internet | HTTP via internal network/VPN |
| **Cost** | LoadBalancer fee | Same LoadBalancer fee |
| **Security** | Exposed to internet | Private network only |
| **Use Case** | Production public APIs | Internal company tools |

## 📋 Prerequisites

- GKE cluster already created (see [../../cluster-setup](../../cluster-setup))
- kubectl configured and authenticated
- Docker installed

## 🚀 Quick Start

### Step 1: Deploy Application

```bash
source config.env
cd scripts
./deploy-application.sh
```

This deploys your application with an Internal LoadBalancer (private IP only).

### Step 2: Get Internal IP Address

```bash
# Wait for IP to be assigned (takes 2-5 minutes)
kubectl get service agent-factory-ai

# Or use utils script
./utils.sh ip
```

You'll get an **internal IP address** like `10.x.x.x` (not a public IP like `34.x.x.x`).

### Step 3: Access from Internal Network

```bash
# From your VPN or internal network
curl http://10.x.x.x
# or browse to http://10.x.x.x

# From another pod in the cluster
curl http://agent-factory-ai.default.svc.cluster.local
```

**Note**: This IP is **NOT accessible** from your local machine unless you're connected to the internal network/VPN!

## 🛠️ Access Methods

### Method 1: Port Forwarding (Recommended for Development)

**Forward service port:**

```bash
# Default: localhost:8080 -> service:80
./utils.sh forward

# Custom ports: localhost:9000 -> service:80
./utils.sh forward 9000 80
```

**Forward directly to pod:**

```bash
# localhost:8080 -> pod:8080
./utils.sh pod-forward
```

### Method 2: From Within Cluster

Other pods in the cluster can access your service directly:

```bash
# Service DNS name (within cluster)
http://agent-factory-ai.default.svc.cluster.local

# Or just the service name (same namespace)
http://agent-factory-ai
```

### Method 3: Cloud IAP Tunnel (For Production Internal Access)

```bash
# Create secure tunnel
./utils.sh tunnel
```

### Method 4: kubectl proxy

```bash
# Start kubectl proxy
kubectl proxy --port=8080

# Access via:
# http://localhost:8080/api/v1/namespaces/default/services/agent-factory-ai:80/proxy/
```

## 📝 Utility Commands

### Access Commands

```bash
# Port forward (interactive)
./utils.sh forward [LOCAL_PORT] [REMOTE_PORT]

# Port forward to specific pod
./utils.sh pod-forward [LOCAL_PORT] [REMOTE_PORT]

# Create IAP tunnel
./utils.sh tunnel [PORT]

# Open shell in pod
./utils.sh shell
```

### Monitoring Commands

```bash
# View logs
./utils.sh logs [LINES]

# Follow logs in real-time
./utils.sh logs-follow

# Check status
./utils.sh status

# Get ClusterIP
./utils.sh ip
```

### Management Commands

```bash
# Scale deployment
./utils.sh scale 3

# Restart deployment
./utils.sh restart

# Delete deployment
./utils.sh delete
```

## 🔧 Configuration

All configuration is the same as `gke-deployment`, the only difference is the service type.

Edit `config.env`:

```bash
export GCP_PROJECT_ID="your-project-id"
export APP_NAME="agent-factory-ai"
export CLUSTER_NAME="ai-agents-cluster"
```

## 🌐 When to Use Internal Deployment

Choose **internal deployment** when:

✅ **Company internal tools** - Admin panels, internal dashboards  
✅ **Private APIs** - APIs for internal teams only  
✅ **VPN-accessible services** - For employees on VPN  
✅ **B2B partner integrations** - Connect via Cloud VPN/Interconnect  
✅ **Development/staging** - Non-public environments  
✅ **Security-sensitive apps** - No internet exposure needed  

Choose **public deployment** (gke-deployment) when:

✅ Production APIs for external clients  
✅ Public-facing web applications  
✅ Mobile app backends  
✅ Services that need to be accessible from internet  

## 🔐 Security Benefits

Internal LoadBalancer provides security advantages:

1. **No Internet Exposure**: Service NOT reachable from public internet
2. **Private IP Only**: Gets internal IP (10.x.x.x) not public IP (34.x.x.x)
3. **VPC Network Only**: Only accessible from your VPC or connected networks
4. **Firewall Protection**: Protected by VPC firewall rules
5. **Access Control**: Control via VPN, Cloud VPN, or Interconnect

## 💡 Common Use Cases

### Development Environment

```bash
# Deploy
cd scripts
./deploy-application.sh

# Access locally
./utils.sh forward
# Browse to http://localhost:8080
```

### Internal Admin Dashboard

```bash
# Deploy with specific name
export APP_NAME="admin-dashboard"
./deploy-application.sh

# Access via port forward
./utils.sh forward 8888 80
# Browse to http://localhost:8888
```

### Microservice Communication

```yaml
# Other services in cluster can access via:
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: client
    env:
    - name: API_URL
      value: "http://agent-factory-ai.default.svc.cluster.local"
```

## 🚀 Deployment Workflow

### First-Time Deployment

```bash
# 1. Ensure cluster exists
cd ../../cluster-setup/scripts
./1-create-cluster.sh
./2-setup-workload-identity.sh

# 2. Deploy application
cd ../../agent-backend/gke-internal-deployment
source config.env
cd scripts
./deploy-application.sh

# 3. Access locally
./utils.sh forward
```

### Update Deployment

```bash
# Just redeploy
cd scripts
./deploy-application.sh

# Automatically does rolling update
```

## 🔍 Troubleshooting

### Port Forward Connection Refused

```bash
# Check if pods are running
./utils.sh status

# Check logs
./utils.sh logs

# Restart deployment
./utils.sh restart
```

### Can't Access from Another Machine

This is expected! Internal deployment is cluster-only. To share access:

```bash
# Option 1: Use Cloud IAP tunnel (requires configuration)
./utils.sh tunnel

# Option 2: Temporarily use public deployment
cd ../gke-deployment
./scripts/deploy-application.sh
```

### Service Not Found

```bash
# Verify service exists
kubectl get services -n default

# Check namespace
kubectl get services --all-namespaces
```

## 📊 Comparison with Other Deployments

```
agent-backend/
├── gke-deployment/           # Public LoadBalancer
│   └── Best for: Production APIs
│
├── gke-internal-deployment/  # Private ClusterIP (THIS)
│   └── Best for: Internal tools, dev environments
│
└── cloud-run-deployment/     # Serverless public
    └── Best for: Auto-scaling public services
```

## 🎯 Best Practices

### 1. Use for Development

Internal deployment is perfect for development:

```bash
# Develop locally, test in cluster
./deploy-application.sh
./utils.sh forward
# Test at http://localhost:8080
```

### 2. Separate Internal and Public Services

```bash
# Internal admin API
export APP_NAME="admin-api"
cd gke-internal-deployment
./scripts/deploy-application.sh

# Public user API
export APP_NAME="user-api"
cd gke-deployment
./scripts/deploy-application.sh
```

### 3. Use IAP for Production Internal Access

For production internal tools, use Cloud IAP:

```bash
# Setup IAP (from cluster-setup)
cd ../../cluster-setup/scripts
./4-setup-iap.sh
```

## 📚 Additional Resources

- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Port Forwarding](https://kubernetes.io/docs/tasks/access-application-cluster/port-forward-access-application-cluster/)
- [Cloud IAP](https://cloud.google.com/iap)

---

**Last Updated**: November 2025  
**Version**: 1.0

**Note**: This deployment keeps your application private and secure. For public access, use [../gke-deployment](../gke-deployment).
