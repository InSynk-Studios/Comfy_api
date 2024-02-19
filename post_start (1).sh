#!/bin/bash

# Update package lists
apt update
apt upgrade -y

# Install build-essential package
apt install -y build-essential
apt install ffmpeg -y

# Install specific Python packages
pip install --upgrade pip
pip install insightface==0.7.3
pip install onnxruntime
pip install onnxruntime-gpu

export TRANSFORMERS_CACHE=/workspace/models

# Check if ./workspace/server/ directory exists
if [ -d "./server/" ]; then
    cd ./server/
    python __init__.py
else
    echo "Directory ./workspace/server/ does not exist."
fi
