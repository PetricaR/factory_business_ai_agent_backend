# Cloud VPN Setup Guide

## Overview

This guide helps you set up **Cloud VPN** to access your internal GKE services from your local network. After setup, you can access your services at their internal IP (e.g., `http://10.x.x.x`) from anywhere!

## 🎯 What You'll Get

After VPN setup:

- ✅ Access internal services from anywhere (home, office, coffee shop)
- ✅ Direct access to internal IP addresses
- ✅ No need for port forwarding
- ✅ Secure encrypted tunnel
- ✅ Team access (everyone on VPN can access)

## 📋 Prerequisites

- GCP project with billing enabled
- Internal LoadBalancer already deployed
- Your home/office public IP address

## 🚀 Quick Setup (Recommended)

### Option 1: Cloud VPN (Site-to-Site)

**Best for**: Connecting your office network to GCP

This creates a permanent VPN tunnel between your network and GCP.

#### Step 1: Get Your Public IP

```bash
# Find your current public IP
curl ifconfig.me
# Example output: 203.0.113.45
```

#### Step 2: Create VPN Gateway

```bash
# Set variables
export PROJECT_ID="formare-ai"
export REGION="europe-west4"
export VPN_GATEWAY_NAME="office-vpn-gateway"
export YOUR_PUBLIC_IP="203.0.113.45"  # Replace with your IP

# Create VPN gateway
gcloud compute vpn-gateways create $VPN_GATEWAY_NAME \
    --network=default \
    --region=$REGION \
    --project=$PROJECT_ID
```

#### Step 3: Reserve Static IP

```bash
# Reserve external IP for VPN
gcloud compute addresses create vpn-static-ip \
    --region=$REGION \
    --project=$PROJECT_ID

# Get the reserved IP
export VPN_IP=$(gcloud compute addresses describe vpn-static-ip \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format='get(address)')

echo "Your VPN IP: $VPN_IP"
```

#### Step 4: Create VPN Tunnel

```bash
# Create VPN tunnel
gcloud compute vpn-tunnels create office-to-gcp-tunnel \
    --peer-address=$YOUR_PUBLIC_IP \
    --region=$REGION \
    --ike-version=2 \
    --shared-secret="YourSecureSharedSecretHere123!" \
    --target-vpn-gateway=$VPN_GATEWAY_NAME \
    --local-traffic-selector=10.0.0.0/8 \
    --remote-traffic-selector=192.168.0.0/16 \
    --project=$PROJECT_ID
```

**Note**: You need to configure your router/firewall to accept this VPN connection.

---

## 🌟 Option 2: Cloud Identity-Aware Proxy (Easiest!)

**Best for**: Individual users, no router configuration needed

IAP creates a secure tunnel without VPN configuration!

### Setup Steps

#### 1. Enable IAP

```bash
# Enable IAP API
gcloud services enable iap.googleapis.com --project=$PROJECT_ID
```

#### 2: Create IAP SSH Tunnel

```bash
# First, ensure you have a GCE instance or use Cloud Shell
# Then create tunnel to your GKE service

# Get the internal IP of your service
export INTERNAL_IP=$(kubectl get service agent-factory-ai -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "Internal IP: $INTERNAL_IP"

# You can access this from Cloud Shell or via IAP Desktop
```

#### 3: Use Cloud Shell (Simplest!)

```bash
# Open Cloud Shell in GCP Console
# https://console.cloud.google.com

# In Cloud Shell:
kubectl get service agent-factory-ai
# Get the internal IP

curl http://10.x.x.x  # Use the internal IP
# Works directly from Cloud Shell!
```

---

## 🖥️ Option 3: IAP Desktop (Windows/Mac App)

**Best for**: Non-technical users, easiest setup

### Setup

1. **Download IAP Desktop**
   - Visit: <https://github.com/GoogleCloudPlatform/iap-desktop/releases>
   - Download and install for Windows or Mac

2. **Configure Access**
   - Open IAP Desktop
   - Login with your Google account
   - Select your GCP project
   - Connect to Cloud Shell or GCE instance

3. **Access Services**
   - From connected instance, use internal IP

   ```bash
   curl http://10.x.x.x
   ```

---

## 🏢 Option 4: Cloud VPN (For Your Router)

**Best for**: Office networks with router access

### High-Level Steps

1. **In GCP Console**:
   - Go to: **Hybrid Connectivity → VPN**
   - Click **Create VPN Connection**
   - Choose **Classic VPN** or **HA VPN**
   - Follow the wizard

2. **Configuration Details**:

```
Name: office-vpn
Gateway: Create new gateway
Region: europe-west4 (match your cluster)
Peer address: YOUR_PUBLIC_IP (from curl ifconfig.me)
IKE version: IKEv2
Shared secret: [Generate strong password]
Routing: Route-based
Remote network ranges: 192.168.0.0/16 (your home/office network)
```

3. **On Your Router** (varies by router):
   - Login to router admin
   - Find VPN settings
   - Create IPsec VPN tunnel
   - Use the shared secret from GCP
   - Set GCP network range: 10.0.0.0/8

### Supported Routers

- pfSense (free, recommended)
- UniFi Dream Machine
- Cisco Meraki
- Fortinet
- Most enterprise routers

---

## 🎯 Recommended Approach for You

### For Quick Testing (Today)

**Use Cloud Shell** (zero configuration):

```bash
# 1. Open: https://console.cloud.google.com
# 2. Click the Cloud Shell icon (top right)
# 3. Run:

kubectl get service agent-factory-ai
export INTERNAL_IP=$(kubectl get service agent-factory-ai -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl http://$INTERNAL_IP

# Now accessible from Cloud Shell!
```

### For Permanent Access (This Week)

**Option A**: If you have router access:

- Set up Cloud VPN (follow Option 4 guide above)
- Takes 1-2 hours one-time setup
- Everyone on your network gets access

**Option B**: If you don't have router access:

- Use **IAP Desktop** (download the app)
- Or keep using **port forwarding**:

  ```bash
  ./scripts/utils.sh forward
  ```

### For Your Team

1. **Short-term** (this week):
   - Share kubectl access
   - Each person runs: `./scripts/utils.sh forward`

2. **Long-term** (next sprint):
   - Set up Cloud VPN at office
   - Or deploy a small bastion host in GCP
   - Or use Cloud IAP

---

## 🔒 Security Best Practices

1. **Use Strong Shared Secrets**

   ```bash
   # Generate strong secret
   openssl rand -base64 32
   ```

2. **Limit VPN Access**

   ```bash
   # Use specific IP ranges, not 0.0.0.0/0
   --local-traffic-selector=10.128.0.0/16
   ```

3. **Enable MFA**
   - Configure IAP with multi-factor authentication
   - Require Google account login

4. **Monitor Access**

   ```bash
   # View VPN logs
   gcloud logging read "resource.type=vpn_gateway" \
       --limit 50 \
       --project=$PROJECT_ID
   ```

---

## 📊 Access Methods Comparison

| Method | Setup Time | Router Needed | Cost | Best For |
|--------|------------|---------------|------|----------|
| **Port Forward** | 0 min | ❌ No | Free | Individual dev |
| **Cloud Shell** | 0 min | ❌ No | Free | Quick testing |
| **IAP Desktop** | 5 min | ❌ No | Free | Individual users |
| **Cloud VPN** | 1-2 hours | ✅ Yes | ~$36/month | Teams/Office |
| **Bastion Host** | 30 min | ❌ No | ~$5/month | Small teams |

---

## 🛠️ Troubleshooting

### Can't Access Internal IP

```bash
# 1. Verify service is up
kubectl get service agent-factory-ai

# 2. Check internal IP assigned
kubectl get service agent-factory-ai -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# 3. Test from within cluster
kubectl run -it --rm debug --image=nicolaka/netshoot --restart=Never -- curl http://10.x.x.x
```

### VPN Not Connecting

```bash
# Check VPN tunnel status
gcloud compute vpn-tunnels describe TUNNEL_NAME \
    --region=$REGION \
    --project=$PROJECT_ID

# Check firewall rules
gcloud compute firewall-rules list --project=$PROJECT_ID
```

---

## 📚 Additional Resources

- [Cloud VPN Overview](https://cloud.google.com/network-connectivity/docs/vpn/concepts/overview)
- [IAP Desktop](https://github.com/GoogleCloudPlatform/iap-desktop)
- [Cloud VPN Setup](https://cloud.google.com/network-connectivity/docs/vpn/how-to)

---

## 🎬 Next Steps

1. **Right Now**: Use Cloud Shell or port forwarding
2. **This Week**: Try IAP Desktop if you need GUI access
3. **Next Month**: Set up proper Cloud VPN for your office

---

**Need help with a specific setup? Let me know which option works best for your situation!**
