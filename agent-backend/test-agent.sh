#!/bin/bash
TOKEN=$(gcloud auth print-identity-token)
APP_URL="https://weather-agent-uiuh5wz4wq-ew.a.run.app"

# 1. Create session first
echo "Creating session..."
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"state": {}}' \
  "$APP_URL/apps/weather_agent/users/test_user/sessions/session_123"

echo -e "\n\n2. Now running agent..."
# 2. Then use the session
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "app_name": "weather_agent",
    "user_id": "test_user",
    "session_id": "session_123",
    "new_message": {
      "role": "user",
      "parts": [{"text": "What is the weather in London? (51.5074, -0.1278)"}]
    }
  }' \
  "$APP_URL/run" | jq