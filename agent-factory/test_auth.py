#!/usr/bin/env python3
"""
Test script to verify service account authentication works
Run this BEFORE running Streamlit to diagnose issues
"""

import os
import sys
from pathlib import Path

print("=" * 70)
print("Service Account Authentication Test")
print("=" * 70)
print()

# Step 1: Check if service account file exists
print("Step 1: Checking service account file...")
print()

service_account_paths = [
    "pandas_agent/auth/formare-ai-gcp.json",
    "auth/formare-ai-gcp.json",
    "./pandas_agent/auth/formare-ai-gcp.json",
]

service_account_file = None
for path in service_account_paths:
    if os.path.exists(path):
        service_account_file = path
        print(f"✅ Found service account: {path}")
        break

if not service_account_file:
    print("❌ Service account file not found!")
    print()
    print("Looked in:")
    for path in service_account_paths:
        print(f"  - {path}")
    print()
    print("Current directory:", os.getcwd())
    print()
    print("Please run this script from your agent-pandas directory")
    sys.exit(1)

print(f"   Full path: {os.path.abspath(service_account_file)}")
print()

# Step 2: Try to load credentials
print("Step 2: Loading credentials...")
print()

try:
    from google.oauth2 import service_account
    
    credentials = service_account.Credentials.from_service_account_file(
        service_account_file,
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    
    print("✅ Credentials loaded successfully")
    print(f"   Service account email: {credentials.service_account_email}")
    print()
    
except Exception as e:
    print(f"❌ Failed to load credentials: {e}")
    sys.exit(1)

# Step 3: Get authentication token
print("Step 3: Getting authentication token...")
print()

try:
    from google.auth.transport.requests import Request
    
    auth_req = Request()
    credentials.refresh(auth_req)
    token = credentials.token
    
    print("✅ Token obtained successfully")
    print(f"   Token (first 50 chars): {token[:50]}...")
    print()
    
except Exception as e:
    print(f"❌ Failed to get token: {e}")
    sys.exit(1)

# Step 4: Test connection to Cloud Run service
print("Step 4: Testing connection to Cloud Run service...")
print()

agent_url = "https://pandas-agent-uiuh5wz4wq-ew.a.run.app"

try:
    import requests
    
    # Try with authentication
    print(f"Testing: {agent_url}/health")
    print("Method: With service account authentication")
    print()
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{agent_url}/health", headers=headers, timeout=10)
    
    print(f"Response: HTTP {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Successfully connected!")
        print()
        print("Response body:")
        import json
        print(json.dumps(response.json(), indent=2))
        print()
        
    elif response.status_code == 403:
        print("❌ HTTP 403 - Forbidden")
        print()
        print("Your service account doesn't have permission to invoke the service.")
        print()
        print("Fix this by running:")
        print()
        print("gcloud run services add-iam-policy-binding pandas-agent \\")
        print("    --region=europe-west1 \\")
        print("    --member=\"serviceAccount:pandas-agent-sa@formare-ai.iam.gserviceaccount.com\" \\")
        print("    --role=\"roles/run.invoker\" \\")
        print("    --project=formare-ai")
        print()
        sys.exit(1)
        
    elif response.status_code == 404:
        print("❌ HTTP 404 - Not Found")
        print()
        print("The agent URL might be incorrect.")
        print()
        print("Check your Cloud Run services:")
        print("  gcloud run services list --region=europe-west1")
        print()
        sys.exit(1)
        
    else:
        print(f"⚠️  Unexpected status code: {response.status_code}")
        print(f"Response: {response.text}")
        print()
        sys.exit(1)
    
except requests.exceptions.ConnectionError as e:
    print(f"❌ Connection error: {e}")
    print()
    print("Check your internet connection and the agent URL")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# Step 5: Test creating a session
print("Step 5: Testing session creation...")
print()

try:
    import uuid
    
    user_id = "test_user"
    session_id = str(uuid.uuid4())
    app_name = "PandasDataScienceAssistant"
    
    session_url = f"{agent_url}/apps/{app_name}/users/{user_id}/sessions/{session_id}"
    
    print(f"Creating session: {session_url}")
    print()
    
    response = requests.post(
        session_url,
        headers=headers,
        json={"state": {}},
        timeout=10
    )
    
    print(f"Response: HTTP {response.status_code}")
    
    if response.status_code in [200, 201]:
        print("✅ Session created successfully!")
        print()
    else:
        print(f"⚠️  Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        print()
        
except Exception as e:
    print(f"⚠️  Session creation test failed: {e}")
    print("This might be okay - the main connection works")
    print()

# Summary
print("=" * 70)
print("Test Summary")
print("=" * 70)
print()
print("✅ Service account file found")
print("✅ Credentials loaded")
print("✅ Authentication token obtained")
print("✅ Connection to Cloud Run successful")
print()
print("🎉 Everything looks good!")
print()
print("Next steps:")
print("  1. Run: streamlit run streamlit_app.py")
print("  2. Click 'Connect' in the sidebar")
print("  3. Start asking pandas questions!")
print()