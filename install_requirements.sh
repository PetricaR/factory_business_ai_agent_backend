#!/bin/bash

# Usage: ./install_requirements.sh [requirements.txt]
# Default file is "requirements.txt" if none is specified

REQ_FILE=${1:-requirements.txt}

if [ ! -f "$REQ_FILE" ]; then
    echo "Error: Requirements file '$REQ_FILE' not found."
    exit 1
fi

# Activate your virtual environment
source adk_env/bin/activate

# Loop through each package in the requirements file
while IFS= read -r PACKAGE || [ -n "$PACKAGE" ]; do
    # Skip empty lines or comments
    [[ "$PACKAGE" =~ ^#.*$ ]] && continue
    [[ -z "$PACKAGE" ]] && continue

    echo "Adding package: $PACKAGE"
    uv add "$PACKAGE" --active
done < "$REQ_FILE"

# Update lock file
echo "Updating uv.lock..."
uv lock

# Sync environment
echo "Syncing adk_env..."
uv sync --active
uv pip freeze > requirements_env.txt
echo "All packages from '$REQ_FILE' have been installed and environment synced."
