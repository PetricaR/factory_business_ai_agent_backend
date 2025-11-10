#!/bin/bash

# setup_gcloud_auth.sh
# Automated Google Cloud Authentication Setup for VS Code on macOS

set -e  # Exit on error

echo "🚀 Google Cloud Authentication Setup Script"
echo "==========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Detect shell configuration file
if [ -f "$HOME/.zshrc" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
    SHELL_NAME="zsh"
elif [ -f "$HOME/.bash_profile" ]; then
    SHELL_CONFIG="$HOME/.bash_profile"
    SHELL_NAME="bash"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_CONFIG="$HOME/.bashrc"
    SHELL_NAME="bash"
else
    echo -e "${YELLOW}⚠️  No shell config file found. Creating ~/.zshrc${NC}"
    SHELL_CONFIG="$HOME/.zshrc"
    SHELL_NAME="zsh"
    touch "$SHELL_CONFIG"
fi

echo -e "📝 Detected shell: ${GREEN}$SHELL_NAME${NC}"
echo -e "📝 Config file: ${GREEN}$SHELL_CONFIG${NC}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ Error: gcloud CLI is not installed${NC}"
    echo ""
    echo "Install it with:"
    echo "  brew install --cask google-cloud-sdk"
    echo ""
    echo "Or download from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

echo -e "${GREEN}✓ gcloud CLI is installed${NC}"
echo ""

# Check if already authenticated
if gcloud auth application-default print-access-token &> /dev/null; then
    echo -e "${YELLOW}⚠️  You're already authenticated${NC}"
    read -p "Do you want to re-authenticate? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping authentication..."
    else
        echo ""
        echo "🔐 Starting authentication process..."
        gcloud auth application-default login
    fi
else
    echo "🔐 Starting authentication process..."
    echo ""
    gcloud auth application-default login
fi

echo ""
echo -e "${GREEN}✓ Authentication completed${NC}"
echo ""

# Set up environment variable
CREDS_PATH="$HOME/.config/gcloud/application_default_credentials.json"
ENV_VAR_LINE="export GOOGLE_APPLICATION_CREDENTIALS=\"$CREDS_PATH\""

# Check if the variable is already in the config file
if grep -q "GOOGLE_APPLICATION_CREDENTIALS" "$SHELL_CONFIG"; then
    echo -e "${YELLOW}⚠️  GOOGLE_APPLICATION_CREDENTIALS already exists in $SHELL_CONFIG${NC}"
    read -p "Do you want to update it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Remove old line and add new one
        sed -i.bak '/GOOGLE_APPLICATION_CREDENTIALS/d' "$SHELL_CONFIG"
        echo "" >> "$SHELL_CONFIG"
        echo "# Google Cloud Application Default Credentials" >> "$SHELL_CONFIG"
        echo "$ENV_VAR_LINE" >> "$SHELL_CONFIG"
        echo -e "${GREEN}✓ Updated environment variable in $SHELL_CONFIG${NC}"
    fi
else
    # Add the environment variable
    echo "" >> "$SHELL_CONFIG"
    echo "# Google Cloud Application Default Credentials" >> "$SHELL_CONFIG"
    echo "$ENV_VAR_LINE" >> "$SHELL_CONFIG"
    echo -e "${GREEN}✓ Added environment variable to $SHELL_CONFIG${NC}"
fi

echo ""

# Export for current session
export GOOGLE_APPLICATION_CREDENTIALS="$CREDS_PATH"

# Verify credentials file exists
if [ -f "$CREDS_PATH" ]; then
    echo -e "${GREEN}✓ Credentials file exists at: $CREDS_PATH${NC}"
else
    echo -e "${RED}❌ Warning: Credentials file not found at: $CREDS_PATH${NC}"
fi

echo ""

# Verify authentication
echo "🔍 Verifying authentication..."
if gcloud auth application-default print-access-token &> /dev/null; then
    echo -e "${GREEN}✓ Authentication verified successfully!${NC}"
else
    echo -e "${RED}❌ Authentication verification failed${NC}"
    exit 1
fi

echo ""
echo "==========================================="
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "==========================================="
echo ""
echo "📋 Next steps:"
echo "  1. Restart VS Code or reload your terminal"
echo "  2. Or run: source $SHELL_CONFIG"
echo ""
echo "🧪 Test your setup with:"
echo "  gcloud auth application-default print-access-token"
echo ""
echo "🐍 In Python, ADC will work automatically:"
echo '  from google.cloud import bigquery'
echo '  client = bigquery.Client()  # No auth needed!'
echo ""

# Offer to reload shell config
read -p "Do you want to reload shell config now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    exec $SHELL -l
fi