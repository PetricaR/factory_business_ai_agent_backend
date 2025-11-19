# Deploying Second Agent to Same Cluster

## Quick Start

Your second agent (`agent_live_audio_and_text`) is ready to deploy to the **same cluster** as your first agent!

### Deploy Second Agent

```bash
cd agent_live_audio_and_text/gke-deployment

# 1. Generate Kubernetes manifests
cd scripts
./generate-k8s.sh

# 2. Deploy to existing cluster
./deploy.sh

# Done! Your second agent is now live alongside the first one
```

---

## Both Agents Running on Same Cluster

### Current Setup

```
Cluster: ai-agents-cluster (europe-west4)
├── agent-factory-ai        # First agent
│   ├── External IP: 34.7.227.11
│   ├── Port: 80 → 8080
│   └── 2 pods running
│
└── agent-audio-text        # Second agent (NEW!)
    ├── External IP: Will be assigned
    ├── Port: 80 → 8080
    └── 2 pods running
```

### Benefits of Same Cluster

✅ **Cost efficient** - Share cluster resources  
✅ **Centralized management** - One cluster to manage  
✅ **Shared authentication** - Same Workload Identity  
✅ **Easy scaling** - Scale agents independently  

---

## How to Deploy

### Step 1: Generate K8s Manifests

```bash
cd agent_live_audio_and_text/gke-deployment/scripts
./generate-k8s.sh
```

This creates:

- `k8s/deployment.yaml` - With app name `agent-audio-text`
- `k8s/service.yaml` - Separate LoadBalancer

### Step 2: Deploy

```bash
./deploy.sh
```

This will:

1. Build Docker image from `agent_live_audio_and_text/`
2. Push to `gcr.io/formare-ai/agent-audio-text:timestamp`
3. Deploy to existing cluster
4. Create new LoadBalancer (different IP)
5. Start 2 pods

### Step 3: Access

```bash
# Get the second agent's IP
kubectl get service agent-audio-text

# Access second agent
http://SECOND_AGENT_IP
```

---

## Managing Multiple Agents

### View All Agents

```bash
# All deployments
kubectl get deployments

# All services
kubectl get services

# All pods
kubectl get pods
```

### View Specific Agent

```bash
# First agent
kubectl get pods -l app=agent-factory-ai
kubectl logs -l app=agent-factory-ai

# Second agent
kubectl get pods -l app=agent-audio-text
kubectl logs -l app=agent-audio-text
```

### Update Specific Agent

```bash
# Update first agent
cd agent-backend/../gke-deployment/scripts
./3-deploy-application.sh

# Update second agent
cd agent_live_audio_and_text/gke-deployment/scripts
./deploy.sh
```

---

## Directory Structure

```
factory_business_ai_agent_backend/
├── agent-backend/              # First agent code
│   └── gke-deployment/         # First agent deployment
│       ├── config.env          # APP_NAME=agent-factory-ai
│       └── scripts/
│           └── 3-deploy-application.sh
│
└── agent_live_audio_and_text/  # Second agent code
    └── gke-deployment/         # Second agent deployment
        ├── config.env          # APP_NAME=agent-audio-text
        └── scripts/
            ├── generate-k8s.sh
            └── deploy.sh
```

---

## Configuration Differences

### First Agent (agent-backend)

```bash
# config.env
export APP_NAME="agent-factory-ai"
export IMAGE_NAME="agent-factory-ai"
```

### Second Agent (agent_live_audio_and_text)

```bash
# config.env
export APP_NAME="agent-audio-text"
export IMAGE_NAME="agent-audio-text"
```

**Different names prevent conflicts!**

---

## Resource Usage

### Cluster Resources

With both agents (2 replicas each):

- **Total pods**: 4 (2 for each agent)
- **Total memory**: ~4GB (1GB limit per pod)
- **Total CPU**: ~4 cores (1 core limit per pod)

### Cost

- **Shared cluster infrastructure** - No extra cluster cost
- **Pay for pods only** - Autopilot charges per pod
- **Estimated**: ~$70-120/month for both agents

---

## Common Commands

### Deploy Both Agents

```bash
# First agent
cd agent-backend/../gke-deployment/scripts
./3-deploy-application.sh

# Second agent  
cd ../../../agent_live_audio_and_text/gke-deployment/scripts
./deploy.sh
```

### Check Status of Both

```bash
kubectl get all
# Shows all deployments, services, pods
```

### Scale Agents Independently

```bash
# Scale first agent to 3 replicas
kubectl scale deployment agent-factory-ai --replicas=3

# Scale second agent to 5 replicas
kubectl scale deployment agent-audio-text --replicas=5
```

### View Logs

```bash
# First agent logs
kubectl logs -l app=agent-factory-ai --tail=50

# Second agent logs
kubectl logs -l app=agent-audio-text --tail=50
```

---

## IP Addresses

Each agent gets its own LoadBalancer IP:

```bash
# First agent IP
kubectl get service agent-factory-ai
# EXTERNAL-IP: 34.7.227.11

# Second agent IP
kubectl get service agent-audio-text
# EXTERNAL-IP: (will be assigned after deployment)
```

**Both are accessible independently!**

---

## Security (IAP for Second Agent)

To secure the second agent with IAP:

```bash
cd agent_live_audio_and_text/gke-deployment/scripts

# Add IAP setup script (use same process as first agent)
# Edit allowed emails in the script
./setup-iap.sh  # Create if needed
```

---

## Summary

✅ **Two agents, one cluster**  
✅ **Independent deployments**  
✅ **Separate IPs**  
✅ **Separate scaling**  
✅ **Shared infrastructure**  
✅ **Easy management**  

**You can add as many agents as you want to the same cluster!**
