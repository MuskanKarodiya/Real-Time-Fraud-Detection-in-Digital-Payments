@echo off
REM ==========================================
REM Week 3 Day 5: Deploy Fraud Detection API to AWS EC2
REM Following project_guide.md Section 6: Cloud Deployment Runbook
REM ==========================================

setlocal enabledelayedexpansion

REM Configuration
set EC2_USER=ubuntu
set EC2_HOST=13.61.71.115
set KEY_PATH=C:\Users\Dell\Downloads\fraud-detection-key.pem
set REMOTE_DIR=/home/ubuntu/fraud-detection-api

echo ========================================
echo Fraud Detection API - EC2 Deployment
echo ========================================
echo.

REM Check if plink/pscp exist (PuTTY tools for Windows SSH/SCP)
where plink >nul 2>&1
if errorlevel 1 (
    echo ERROR: plink not found. Please install PuTTY or use Git Bash.
    echo.
    echo Alternative: Use Git Bash and run deploy-to-ec2.sh
    pause
    exit /b 1
)

echo [1/7] Checking prerequisites...
if not exist "%KEY_PATH%" (
    echo ERROR: Key file not found at %KEY_PATH%
    pause
    exit /b 1
)
echo [OK] Key file found

echo.
echo [2/7] Testing SSH connection...
plink -i "%KEY_PATH%" -batch %EC2_USER%@%EC2_HOST% "echo 'SSH connection successful'"
if errorlevel 1 (
    echo ERROR: SSH connection failed
    pause
    exit /b 1
)

echo.
echo [3/7] Installing Docker on EC2...
plink -i "%KEY_PATH%" %EC2_USER%@%EC2_HOST% "sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin || (command -v docker && echo 'Docker already installed')"

echo.
echo [4/7] Copying application files...
plink -i "%KEY_PATH%" %EC2_USER%@%EC2_HOST% "mkdir -p %REMOTE_DIR%/logs"
pscp -i "%KEY_PATH%" -r Dockerfile docker-compose.yml requirements.txt app models %EC2_USER%@%EC2_HOST%:%REMOTE_DIR%/

echo.
echo [5/7] Building Docker image on EC2...
plink -i "%KEY_PATH%" %EC2_USER%@%EC2_HOST% "cd %REMOTE_DIR% && sudo docker build -t fraud-detection-api:v1.0 ."

echo.
echo [6/7] Deploying container...
plink -i "%KEY_PATH%" %EC2_USER}@%EC2_HOST% "cd %REMOTE_DIR% && sudo docker stop fraud-detection-api 2>/dev/null || true && sudo docker rm fraud-detection-api 2>/dev/null || true && sudo docker run -d --name fraud-detection-api --restart unless-stopped -p 8000:8000 -v /home/ubuntu/fraud-detection-api/logs:/app/logs -e PYTHONUNBUFFERED=1 fraud-detection-api:v1.0"

echo.
echo [7/7] Validating deployment...
timeout /t 5 /nobreak >nul
plink -i "%KEY_PATH%" %EC2_USER%@%EC2_HOST% "curl -s http://localhost:8000/api/v1/health"

echo.
echo ========================================
echo Deployment Complete!
echo ========================================
echo.
echo API Endpoints:
echo   Health Check: http://13.61.71.115:8000/api/v1/health
echo   Predict:      http://13.61.71.115:8000/api/v1/predict
echo   Model Info:   http://13.61.71.115:8000/api/v1/model/info
echo   Docs:         http://13.61.71.115:8000/docs
echo.

pause
