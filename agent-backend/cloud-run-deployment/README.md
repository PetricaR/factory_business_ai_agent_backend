# Cloud Run Deployment

## Overview

This directory contains scripts for **deploying applications to Google Cloud Run**. Cloud Run is a fully managed serverless platform that automatically scales your containerized applications.

## 📋 Why Cloud Run?

- ✅ **Fully Serverless**: No infrastructure management
- ✅ **Auto-scaling**: Scales to zero when not in use
- ✅ **Pay-per-use**: Only pay for actual usage
- ✅ **Fast Deployment**: Deploy in seconds
- ✅ **HTTPS by default**: Automatic SSL certificates
- ✅ **Custom domains**: Easy domain mapping

## 🚀 Quick Start

### Prerequisites

- Google Cloud SDK (`gcloud`)
- Docker installed and running
- Active GCP project with billing enabled
- Cloud Run API enabled

### Step 1: Configure

Edit `config.env` with your settings:

```bash
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="europe-west4"
export APP_NAME="agent-factory-ai"
```

Load the configuration:

```bash
source config.env
```

### Step 2: Deploy

Deploy your application with a single command:

```bash
cd scripts
chmod +x *.sh
./deploy.sh
```

This script will:

1. Build Docker image for `linux/amd64`
2. Push image to Google Container Registry
3. Deploy to Cloud Run
4. Display service URL

### Step 3: Access Your Application

After deployment, get your service URL:

```bash
./utils.sh url
```

Access your application at the provided URL.

## 📝 Scripts Reference

| Script | Purpose | Duration |
|--------|---------|----------|
| `deploy.sh` | Full deployment pipeline | 2-5 min |
| `utils.sh` | Utility commands | Instant |

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GCP_PROJECT_ID` | `formare-ai` | Your GCP project ID |
| `GCP_REGION` | `europe-west4` | Cloud Run region |
| `APP_NAME` | `agent-factory-ai` | Application name |
| `MEMORY` | `1Gi` | Memory allocation |
| `CPU` | `1` | CPU allocation |
| `MAX_INSTANCES` | `10` | Maximum instances |
| `MIN_INSTANCES` | `0` | Minimum instances (0 = scale to zero) |
| `TIMEOUT` | `300` | Request timeout (seconds) |
| `CONCURRENCY` | `80` | Max concurrent requests per instance |
| `ALLOW_UNAUTHENTICATED` | `true` | Allow public access |

### Resource Configuration

Edit `config.env` to adjust resources:

```bash
# Increase memory and CPU
export MEMORY="2Gi"
export CPU="2"

# Keep minimum instances to avoid cold starts
export MIN_INSTANCES="1"

# Increase max instances for high traffic
export MAX_INSTANCES="20"
```

## 🛠️ Utility Commands

The `utils.sh` script provides helpful commands:

### View Logs

```bash
# Last 100 lines
./utils.sh logs

# Last 200 lines
./utils.sh logs 200
```

### Get Service URL

```bash
./utils.sh url
```

### Check Service Status

```bash
./utils.sh status
```

### Scale Service

```bash
# Set min=1, max=5 instances
./utils.sh scale 1 5

# Scale to zero (serverless)
./utils.sh scale 0 10
```

### Update Environment Variables

```bash
./utils.sh set-env "API_KEY=your-key,DEBUG=true"
```

### Update Memory

```bash
./utils.sh set-memory 2Gi
```

### Update CPU

```bash
./utils.sh set-cpu 2
```

### List Revisions

```bash
./utils.sh revisions
```

### Rollback to Previous Revision

```bash
./utils.sh rollback
```

### Delete Service

```bash
./utils.sh delete
```

## 🔄 Deployment Workflow

### First-Time Deployment

```bash
# Configure
source config.env

# Deploy
cd scripts
./deploy.sh
```

### Update Deployment

Simply re-run the deployment script:

```bash
cd scripts
./deploy.sh
```

Cloud Run will:

- Create a new revision
- Gradually shift traffic to the new revision
- Keep previous revisions for rollback

## 🌟 Cloud Run Features

### Auto-scaling

Cloud Run automatically scales based on traffic:

```bash
# Scale to zero when idle (cost-effective)
export MIN_INSTANCES="0"

# Keep warm instances (no cold starts)
export MIN_INSTANCES="1"
```

### Traffic Splitting

Deploy new versions gradually:

```bash
# Deploy new revision
./deploy.sh

# Split traffic 50/50 between revisions
gcloud run services update-traffic $SERVICE_NAME \
  --to-revisions=LATEST=50,PREVIOUS=50
```

### Custom Domains

Map your domain:

```bash
# Map domain
gcloud run domain-mappings create \
  --service=$SERVICE_NAME \
  --domain=app.example.com \
  --region=$REGION
```

### Environment Variables

Set runtime environment variables:

```bash
# Via utils script
./utils.sh set-env "KEY1=value1,KEY2=value2"

# Or during deployment
gcloud run deploy $SERVICE_NAME \
  --set-env-vars="KEY1=value1,KEY2=value2"
```

### Secrets

Use Google Secret Manager for sensitive data:

```bash
# Create secret
echo -n "my-secret-value" | gcloud secrets create my-secret --data-file=-

# Reference in Cloud Run
gcloud run services update $SERVICE_NAME \
  --set-secrets="API_KEY=my-secret:latest"
```

## 🔍 Troubleshooting

### Service Not Responding

Check logs:

```bash
./utils.sh logs 500
```

### Cold Start Issues

Set minimum instances:

```bash
./utils.sh scale 1 10
```

### Memory/CPU Issues

Increase resources:

```bash
./utils.sh set-memory 2Gi
./utils.sh set-cpu 2
```

### Timeout Errors

Increase timeout in `config.env`:

```bash
export TIMEOUT="600"  # 10 minutes
```

Then redeploy:

```bash
./deploy.sh
```

## 📊 Monitoring

### View Logs in Real-time

```bash
gcloud run services logs tail $SERVICE_NAME --region=$REGION
```

### View Metrics

Visit [Cloud Console](https://console.cloud.google.com/run) to see:

- Request count
- Latency
- Instance count
- Memory/CPU usage

## 💰 Cost Optimization

### Tips to Reduce Costs

1. **Scale to zero**: Set `MIN_INSTANCES=0` for low-traffic apps
2. **Right-size resources**: Don't over-provision memory/CPU
3. **Use caching**: Implement caching to reduce requests
4. **Set concurrency**: Higher concurrency = fewer instances

### Pricing Model

Cloud Run charges for:

- **CPU**: Only while processing requests
- **Memory**: While instance is running
- **Requests**: Number of requests

See [Cloud Run Pricing](https://cloud.google.com/run/pricing)

## 🎯 Best Practices

### 1. Use .dockerignore

Reduce image size:

```
# .dockerignore
__pycache__
*.pyc
*.db
.env
.git
```

### 2. Optimize Dockerfile

Use multi-stage builds and minimal base images.

### 3. Health Checks

Implement `/health` endpoint:

```python
@app.get("/health")
def health():
    return {"status": "healthy"}
```

### 4. Graceful Shutdown

Handle SIGTERM for graceful shutdown:

```python
import signal
import sys

def signal_handler(sig, frame):
    print('Shutting down gracefully...')
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
```

### 5. Use Secrets Manager

Never hardcode secrets - use Secret Manager.

## 🔐 Authentication

### Public Access

```bash
export ALLOW_UNAUTHENTICATED="true"
```

### Private Access (IAM)

```bash
export ALLOW_UNAUTHENTICATED="false"
```

Then grant specific users access:

```bash
gcloud run services add-iam-policy-binding $SERVICE_NAME \
  --member="user:email@example.com" \
  --role="roles/run.invoker"
```

## 📚 Additional Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Run Pricing](https://cloud.google.com/run/pricing)
- [Cloud Run Limits](https://cloud.google.com/run/quotas)
- [Best Practices](https://cloud.google.com/run/docs/best-practices)

## 🔄 Comparison: Cloud Run vs GKE

| Feature | Cloud Run | GKE |
|---------|-----------|-----|
| **Management** | Fully managed | Self-managed |
| **Scaling** | Automatic (0-N) | Manual/HPA |
| **Cost** | Pay-per-use | Pay for nodes |
| **Cold Starts** | Yes | No |
| **Complexity** | Simple | Complex |
| **Control** | Limited | Full |
| **Best For** | Web apps, APIs | Complex workloads |

Choose **Cloud Run** for:

- Simple web applications and APIs
- Variable/unpredictable traffic
- Cost optimization (pay-per-use)
- Quick deployments

Choose **GKE** for:

- Complex microservices
- Stateful applications
- Custom networking requirements
- Maximum control

---

**Last Updated**: November 2025  
**Version**: 1.0
