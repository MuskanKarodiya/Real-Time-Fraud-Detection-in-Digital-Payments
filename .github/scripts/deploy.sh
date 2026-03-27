#!/bin/bash
#
# Deployment Script for Fraud Detection API
# This script runs on EC2 via SSH from GitHub Actions
#
# Usage: ./deploy.sh [branch]
#   branch defaults to 'main'
#

set -e  # Exit on error

# Configuration
REPO_NAME="Real-Time-Fraud-Detection-in-Digital-Payments"
REPO_URL="https://github.com/MuskanKarodiya/$REPO_NAME.git"
BRANCH=${1:-main}
PROJECT_DIR="/home/ubuntu/fraud-detection-api"
DOCKER_IMAGE="fraud-detection-api:latest"
CONTAINER_NAME="fraud-api"

echo "=========================================="
echo "  Fraud Detection API - Deployment"
echo "=========================================="
echo "Branch: $BRANCH"
echo ""

# Step 1: Update system packages
echo "[1/6] Updating system packages..."
sudo apt-get update -qq

# Step 2: Ensure Docker is installed
echo "[2/6] Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Installing..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker ubuntu
    echo "Docker installed. Please log out and back in for group changes to take effect."
    exit 1
fi
docker --version

# Step 3: Stop existing container if running
echo "[3/6] Stopping existing container..."
if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
    echo "Stopping running container..."
    docker stop $CONTAINER_NAME
fi

# Step 4: Remove old container (if exists)
echo "[4/6] Removing old container..."
if docker ps -aq -f name=$CONTAINER_NAME | grep -q .; then
    echo "Removing old container..."
    docker rm $CONTAINER_NAME
fi

# Step 5: Pull latest code
echo "[5/6] Pulling latest code..."
if [ -d "$PROJECT_DIR" ]; then
    cd $PROJECT_DIR
    git fetch origin
    git checkout $BRANCH
    git pull origin $BRANCH
else
    echo "Cloning repository..."
    git clone -b $BRANCH $REPO_URL $PROJECT_DIR
    cd $PROJECT_DIR
fi

# Step 6: Build and run Docker container
echo "[6/6] Building and starting container..."
docker build -t $DOCKER_IMAGE .
docker run -d \
    --name $CONTAINER_NAME \
    -p 8000:8000 \
    -v $PROJECT_DIR/logs:/app/logs \
    --restart unless-stopped \
    $DOCKER_IMAGE

# Verify deployment
echo ""
echo "=========================================="
echo "  Verifying Deployment..."
echo "=========================================="
sleep 5

# Health check
if curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo "✓ API is healthy!"
    echo ""
    echo "Deployment successful!"
    echo "API running at: http://13.61.71.115:8000"
    echo "Health check: http://13.61.71.115:8000/api/v1/health"
else
    echo "✗ Health check failed!"
    echo "Container logs:"
    docker logs $CONTAINER_NAME --tail 50
    exit 1
fi
