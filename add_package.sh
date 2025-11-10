#!/bin/bash

# Usage: ./add_package.sh <package-name>

PACKAGE_NAME=$1

if [ -z "$PACKAGE_NAME" ]; then
  echo "Error: No package specified."
  echo "Usage: $0 <package-name>"
  exit 1
fi

# Activate your virtual environment
source adk_env/bin/activate

# Add the package using uv with --active
echo "Adding package: $PACKAGE_NAME"
uv add "$PACKAGE_NAME" --active

# Update the lock file
echo "Updating uv.lock..."
uv lock

# Sync environment with --active
echo "Syncing adk_env..."
uv sync --active

echo "Done! Package '$PACKAGE_NAME' added and environment synced in adk_env."
