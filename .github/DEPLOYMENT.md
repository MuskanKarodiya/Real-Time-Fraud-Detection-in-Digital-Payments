# CI/CD Setup Instructions

This document explains how to configure GitHub Secrets for automated deployment to EC2.

## Required GitHub Secrets

You need to add ONE secret to your GitHub repository:

### Secret: `EC2_SSH_PRIVATE_KEY`

This is the contents of your AWS EC2 key pair file (`.pem` file).

#### Steps to add:

1. **Get your private key content:**
   ```bash
   # On Windows (Git Bash)
   cat /c/Users/Dell/Downloads/fraud-detection-key.pem
   ```

2. **Copy the entire output** (including `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----`)

3. **Go to GitHub repository settings:**
   - Navigate to: https://github.com/MuskanKarodiya/Real-Time-Fraud-Detection-in-Digital-Payments/settings/secrets/actions
   - Click: "New repository secret"
   - Name: `EC2_SSH_PRIVATE_KEY`
   - Value: [Paste the key content]
   - Click: "Add secret"

## Deployment Flow

When you push to `main` branch:

```
push to main
    ↓
[1] Tests run (pytest)
    ↓
[2] Docker image built & tested
    ↓
[3] Deploy job runs:
    - SSH to EC2 using the key
    - Run deploy.sh script
    - Build & start Docker container
    - Health check verification
```

## EC2 Instance Details

| Property | Value |
|----------|-------|
| Public IP | 13.61.71.115 |
| User | ubuntu |
| Region | eu-north-1 |
| SSH Port | 22 |

## Manual Deployment (if needed)

If you need to deploy manually without CI/CD:

```bash
# Connect to EC2
ssh -i /c/Users/Dell/Downloads/fraud-detection-key.pem ubuntu@13.61.71.115

# Run deployment script on EC2
cd /home/ubuntu
chmod +x deploy.sh
./deploy.sh main
```

## Troubleshooting

### Issue: "Permission denied (publickey)"
- Ensure the `EC2_SSH_PRIVATE_KEY` secret contains the complete key file
- Verify the key file matches the one associated with your EC2 instance

### Issue: "Host key verification failed"
- The workflow automatically adds the host key via `ssh-keyscan`
- If still failing, your EC2 IP may have changed

### Issue: Health check fails
- SSH into EC2 manually
- Check container status: `docker ps -a`
- View container logs: `docker logs fraud-api`
- Restart if needed: `docker restart fraud-api`
