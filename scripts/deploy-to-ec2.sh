#!/bin/bash
#############################################
# Week 3 Day 5: Deploy Fraud Detection API to AWS EC2
# Following project_guide.md Section 6: Cloud Deployment Runbook
#############################################

set -e  # Exit on error

# EC2 Configuration
EC2_USER="ubuntu"
EC2_HOST="13.61.71.115"
KEY_PATH="/c/Users/Dell/Downloads/fraud-detection-key.pem"
REMOTE_DIR="/home/ubuntu/fraud-detection-api"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Fraud Detection API - EC2 Deployment ===${NC}"
echo ""

# Step 1: Check prerequisites
echo -e "${GREEN}[1/7]${NC} Checking prerequisites..."
if [ ! -f "$KEY_PATH" ]; then
    echo "Error: Key file not found at $KEY_PATH"
    echo "Please update KEY_PATH in this script"
    exit 1
fi
chmod 400 "$KEY_PATH"
echo "✓ Key file configured"

# Step 2: Test SSH connection
echo -e "${GREEN}[2/7]${NC} Testing SSH connection..."
ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_HOST}" "echo '✓ SSH connection successful'" || exit 1

# Step 3: Install Docker on EC2 (if not already installed)
echo -e "${GREEN}[3/7]${NC} Ensuring Docker is installed on EC2..."
ssh -i "$KEY_PATH" "${EC2_USER}@${EC2_HOST}" << 'ENDSSH'
    # Update package list
    sudo apt-get update

    # Install Docker if not present
    if ! command -v docker &> /dev/null; then
        echo "Installing Docker..."
        sudo apt-get install -y ca-certificates curl gnupg
        sudo install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        sudo chmod a+r /etc/apt/keyrings/docker.gpg
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
          $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
          sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        sudo usermod -aG docker ubuntu
        echo "✓ Docker installed"
    else
        echo "✓ Docker already installed"
    fi

    # Install Docker Compose if not present
    if ! command -v docker-compose &> /dev/null; then
        echo "Installing Docker Compose..."
        sudo apt-get install -y docker-compose
        echo "✓ Docker Compose installed"
    else
        echo "✓ Docker Compose already installed"
    fi
ENDSSH

# Step 4: Create remote directory and copy files
echo -e "${GREEN}[4/7]${NC} Copying application files to EC2..."
ssh -i "$KEY_PATH" "${EC2_USER}@${EC2_HOST}" "mkdir -p $REMOTE_DIR/logs"

# Copy required files
scp -i "$KEY_PATH" -r \
    Dockerfile \
    docker-compose.yml \
    requirements.txt \
    app/ \
    models/ \
    "${EC2_USER}@${EC2_HOST}:${REMOTE_DIR}/"

echo "✓ Files copied to EC2"

# Step 5: Build Docker image on EC2
echo -e "${GREEN}[5/7]${NC} Building Docker image on EC2..."
ssh -i "$KEY_PATH" "${EC2_USER}@${EC2_HOST}" << ENDSSH
    cd $REMOTE_DIR
    docker build -t fraud-detection-api:v1.0 .
ENDSSH
echo "✓ Docker image built"

# Step 6: Stop existing container and start new one
echo -e "${GREEN}[6/7]${NC} Deploying container..."
ssh -i "$KEY_PATH" "${EC2_USER}@${EC2_HOST}" << ENDSSH
    cd $REMOTE_DIR

    # Stop and remove existing container
    docker stop fraud-detection-api 2>/dev/null || true
    docker rm fraud-detection-api 2>/dev/null || true

    # Run new container
    docker run -d \
        --name fraud-detection-api \
        --restart unless-stopped \
        -p 8000:8000 \
        -v /home/ubuntu/fraud-detection-api/logs:/app/logs \
        -e PYTHONUNBUFFERED=1 \
        fraud-detection-api:v1.0

    echo "✓ Container started"
ENDSSH

# Step 7: Validate deployment
echo -e "${GREEN}[7/7]${NC} Validating deployment..."
sleep 5  # Give container time to start

# Health check
HEALTH_CHECK=$(ssh -i "$KEY_PATH" "${EC2_USER}@${EC2_HOST}" "curl -s http://localhost:8000/api/v1/health" || echo "failed")

if echo "$HEALTH_CHECK" | grep -q "healthy"; then
    echo -e "${GREEN}✓ Deployment successful!${NC}"
    echo ""
    echo "API Endpoints:"
    echo "  Health Check: http://13.61.71.115:8000/api/v1/health"
    echo "  Predict:      http://13.61.71.115:8000/api/v1/predict"
    echo "  Model Info:   http://13.61.71.115:8000/api/v1/model/info"
    echo "  Documentation: http://13.61.71.115:8000/docs"
    echo ""
    echo "Response from health check:"
    echo "$HEALTH_CHECK"
else
    echo "❌ Health check failed. Checking container logs..."
    ssh -i "$KEY_PATH" "${EC2_USER}@${EC2_HOST}" "docker logs fraud-detection-api --tail 50"
    exit 1
fi
