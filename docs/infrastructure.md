# Infrastructure Details

**FraudLens - Real-Time Fraud Detection System**

*Last Updated: 2026-03-27*

---

## AWS EC2 Instance

| Property | Value |
|----------|-------|
| **Instance ID** | i-0d12c6ebf970a2b34 |
| **Public IP** | 13.61.71.115 (Elastic IP) |
| **Private IP** | 172.31.27.192 |
| **AMI** | Ubuntu Server 24.04.3 LTS (HVM) |
| **Instance Type** | t3.medium (2 vCPU, 4GB RAM) |
| **Storage** | 20 GB SSD (gp3) |
| **Region** | Asia Pacific (Mumbai) - ap-south-1 |

### Key Change from Initial Setup
- **Originally**: t3.micro (1GB RAM) → **Upgraded to t3.medium** (4GB RAM)
- **Reason**: Memory overflow issues with 284K rows. t3.medium provides sufficient RAM for data processing and model operations.

---

## SSH Connection

### From Windows (Git Bash)

```bash
ssh -i "C:/Users/Dell/Downloads/fraud-detection-key.pem" ubuntu@13.61.71.115
```

### From Windows (PowerShell)

```powershell
ssh -i "C:\Users\Dell\Downloads\fraud-detection-key.pem" ubuntu@13.61.71.115
```

### From Linux/Mac

```bash
ssh -i ~/Downloads/fraud-detection-key.pem ubuntu@13.61.71.115
```

**Key File Permissions:**
```bash
# On Windows: Set in properties → Security → Advanced
# On Linux/Mac:
chmod 400 fraud-detection-key.pem
```

---

## PostgreSQL Database

### Connection Details

| Property | Value |
|----------|-------|
| **Version** | PostgreSQL 16.13 |
| **Database Name** | fraud_detection |
| **Host** | localhost (from within EC2) / 13.61.71.115 (from external with VPN) |
| **Port** | 5432 |
| **Default User** | postgres |
| **Password** | See `.env` file on EC2 (`/home/ubuntu/.env`) |

### Start/Stop PostgreSQL

```bash
# Start PostgreSQL
sudo systemctl start postgresql

# Stop PostgreSQL
sudo systemctl stop postgresql

# Check status
sudo systemctl status postgresql

# Connect to database
sudo -u postgres psql -d fraud_detection
```

### Database Connection from Local Machine

```python
import psycopg2

conn = psycopg2.connect(
    host="13.61.71.115",
    port=5432,
    database="fraud_detection",
    user="postgres",
    password="<your_password>",
    connect_timeout=5
)
```

---

## Database Tables

| Table | Purpose | Rows | Key Columns |
|-------|---------|------|-------------|
| `transactions_raw` | Raw ingested transaction data | 284,807 | id, time_elapsed, v1-v28, amount, class |
| `transactions_features` | Engineered features for ML | 284,807 | id, amount_scaled, hour, is_night, hour_sin, hour_cos |
| `transactions_training` | Features + labels for retraining | 284,807 | id, time_elapsed, v1-v28, amount, amount_scaled, hour_sin, hour_cos, class |
| `predictions_log` | All API predictions | N/A | id, transaction_id, prediction, confidence, risk_level, model_version, latency_ms, predicted_at |
| `prediction_inputs` | V1-V28 features for drift monitoring | N/A | transaction_id, v1-v28 |
| `error_logs` | API errors with timestamps | N/A | id, endpoint, error_type, error_message, transaction_id, amount, predicted_at |
| `alerts_log` | Alert history with email status | N/A | id, alert_type, severity, title, message, details, email_sent, created_at |
| `retraining_log` | Retraining run history | N/A | id, run_id, triggered_by, status, roc_auc, precision, recall, promoted, new_model_version |
| `pipeline_audit` | ETL pipeline run logs | N/A | id, pipeline_name, started_at, completed_at, status, rows_processed |

### Table Sizes (Approximate)

| Table | Estimated Size |
|-------|---------------|
| transactions_raw | ~80 MB |
| transactions_features | ~120 MB |
| transactions_training | ~150 MB |
| predictions_log | Grows with predictions |
| prediction_inputs | Grows with predictions |

---

## Security Group Rules

| Port | Protocol | Source | Purpose | Status |
|------|----------|--------|---------|--------|
| 22 | TCP | Your IP (from .gitconfig) | SSH access | ✅ Active |
| 8000 | TCP | 0.0.0.0/0 | FastAPI | ✅ Active |
| 8501 | TCP | 0.0.0.0/0 | Streamlit (future) | ⏳ Not exposed |
| 5432 | TCP | localhost only | PostgreSQL | ✅ Local only |

### Adding Your IP to Security Group

1. Go to EC2 Console → Security Groups
2. Find the security group attached to your instance
3. Inbound Rules → Edit Inbound Rules → Add Rule
4. Type: Custom TCP, Port: 22, Source: Your IP
5. Click Save

---

## Docker Deployment

### Container Details

| Property | Value |
|----------|-------|
| **Container Name** | fraud-detection-api |
| **Image** | fraud-detection-api:latest |
| **Port Mapping** | 8000:8000 (host:container) |
| **Restart Policy** | unless-stopped |
| **Health Check** | curl -f http://localhost:8000/api/v1/homes |

### Docker Commands

```bash
# View running containers
docker ps

# View container logs
docker logs fraud-detection-api

# Follow logs in real-time
docker logs -f fraud-detection-api

# Restart container
docker restart fraud-detection-api

# Stop container
docker stop fraud-detection-api

# Remove container
docker rm fraud-detection-api
```

### Docker Compose (for local development)

```bash
# Build and start
docker-compose up --build

# Stop and remove
docker-compose down

# View logs
docker-compose logs -f api
```

### Rebuilding the Image

```bash
# On EC2
cd /home/ubuntu/fraud-detection-system

# Stop container
docker stop fraud-detection-api

# Remove old container
docker rm fraud-detection-api

# Rebuild image
docker build -t fraud-detection-api:latest .

# Run new container
docker run -d --name fraud-detection-api \
  -p 8000:8000 \
  --restart unless-stopped \
  fraud-detection-api:latest
```

---

## File Locations on EC2

| Path | Contents |
|------|----------|
| `/home/ubuntu/` | Main project files |
| `/home/ubuntu/fraud-detection-api/` | Docker volume (if using) |
| `/home/ubuntu/models/` | Model artifacts |
| `/var/log/fraud_alerts.log` | Alerting cron logs |
| `/home/ubuntu/.env` | Environment variables (DB credentials, email) |

### Copied Files (for standalone execution)

The following files are copied to `/home/ubuntu/` for standalone Python execution:

| File | Purpose |
|------|---------|
| `retraining.py` | Automated retraining pipeline |
| `populate_training.py` | Populate training table |
| `alerting.py` | Monitoring and email alerts |
| `monitoring.py` | Drift detection (PSI, KS test) |
| `feature_engineering.py` | Feature transformations |
| `model_training.py` | Model training utilities |
| `data_ingestion.py` | Data loading |
| `config.py` | Configuration |
| `models/optuna_study.pkl` | Hyperparameters |
| `models/metadata.json` | Baseline metrics |
| `models/fraud_detector_v1.pkl` | Production model |

---

## Python Environment on EC2

### Installed Python Version

```bash
python3 --version
# Output: Python 3.12.3
```

### Installed Packages

```bash
# Core ML/DL
pip3 install --break-system-packages scikit-learn xgboost joblib seaborn

# Database
pip3 install --break-system-packages psycopg2-binary

# Numerical (downgraded for sklearn compatibility)
pip3 install --break-system-packages 'numpy<2'

# Dashboard (not used on EC2, but available)
pip3 install --break-system-packages plotly
```

### Python Dependencies List

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
psycopg2-binary==2.9.9
python-dotenv==1.0.0
joblib==1.3.2
scikit-learn==1.3.2
xgboost==2.0.3
pandas==2.0.3
numpy==1.26.4
```

---

## Environment Variables

### `/home/ubuntu/.env` (EC2)

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fraud_detection
DB_USER=postgres
DB_PASSWORD=<your_password>

# Email Alerts
ALERT_EMAIL_ENABLED=true
ALERT_SENDER_EMAIL=karodiyamuskan2@gmail.com
ALERT_SENDER_PASSWORD=<app_specific_password>
ALERT_RECIPIENTS=karodiyamuskan2@gmail.com
```

### Local `.env` (for local development)

```bash
# API Configuration
API_BASE_URL=http://13.61.71.115:8000
API_KEY=dev-key-12345

# Database Configuration (for local dashboard to connect to EC2)
DB_HOST=13.61.71.115
DB_PORT=5432
DB_NAME=fraud_detection
DB_USER=postgres
DB_PASSWORD=<your_password>

# Email Alerts (for local testing)
ALERT_EMAIL_ENABLED=false
```

---

## Cron Jobs

### Alerting Monitor (Every 5 minutes)

```bash
*/5 * * * * cd /home/ubuntu && /usr/bin/python3 alerting.py >> /var/log/fraud_alerts.log 2>&1
```

### View Cron Jobs

```bash
crontab -l
```

### Edit Cron Jobs

```bash
crontab -e
```

---

## Useful Commands

### System Monitoring

```bash
# Check CPU and memory usage
htop

# Check disk usage
df -h

# Check running processes
ps aux | grep python

# View systemd logs
journalctl -u ubuntu -xe
```

### Docker Operations

```bash
# View container resource usage
docker stats fraud-detection-api

# Execute command inside container
docker exec -it fraud-detection-api bash

# Copy file from container to host
docker cp fraud-detection-api:/app/models/metadata.json .

# Copy file from host to container
docker cp metadata.json fraud-detection-api:/app/models/
```

### Database Operations

```bash
# Connect to database
sudo -u postgres psql -d fraud_detection

# Useful queries
\dt                          # List tables
\d+ predictions_log           # Describe table
SELECT COUNT(*) FROM predictions_log;
SELECT * FROM alerts_log ORDER BY created_at DESC LIMIT 5;
```

---

## Cost Breakdown (Estimated)

| Resource | Cost (Monthly) |
|----------|---------------|
| EC2 (t3.medium, Mumbai) | ~$25-30/month |
| Elastic IP | ~$3/month |
| Data Transfer (1 GB/month) | ~$0.08/month |
| Storage (20 GB SSD) | ~$2/month |
| **Total** | **~$30-35/month** |

---

## Troubleshooting

### Issue: Container won't start

```bash
# Check logs
docker logs fraud-detection-api

# Check if port is already in use
sudo netstat -tulpn | grep 8000

# Restart Docker service
sudo systemctl restart docker
```

### Issue: Database connection refused

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Start PostgreSQL if stopped
sudo systemctl start postgresql

# Check if port is listening
sudo netstat -tulpn | grep 5432
```

### Issue: API returns 401 Unauthorized

- Verify `X-API-Key` header is included
- Check key is valid: `dev-key-12345`, `test-key-67890`
- Check API key configuration in `app/auth.py`

### Issue: Out of memory errors

- t3.medium has 4GB RAM - ensure no other large processes running
- Monitor memory: `htop`
- Consider upgrading to t3.large (8GB RAM) if needed

---

## Backup & Recovery

### Database Backup

```bash
# Create backup
sudo -u postgres pg_dump -d fraud_detection > backup_$(date +%Y%m%d).sql

# Restore from backup
sudo -u postgres psql -d fraud_detection < backup_20260327.sql
```

### Model Artifact Backup

```bash
# Models are stored in:
/home/ubuntu/models/

# Backup to S3 (if configured)
aws s3 cp /home/ubuntu/models/fraud_detector_v1.pkl s3://backup-bucket/

# Local backup
cp /home/ubuntu/models/fraud_detector_v1.pkl /home/ubuntu/backup/
```

---

## Scaling Considerations

### Current Limits (t3.medium)

| Metric | Current Value | Limit |
|--------|---------------|-------|
| RAM | 4GB | ~4GB |
| CPU | 2 vCPU | ~2 vCPU |
| Storage | 20GB | ~20GB |
| Network | Low/Moderate | Up to 5 Gbps |

### Upgrade Path

| Need | Recommended Instance Type |
|------|----------------------|
| More RAM for training | t3.large (8GB RAM) |
| More CPU for batch processing | t3.xlarge (4 vCPU) |
| Production traffic | m5.large or m5.xlarge |

---

## Next Steps

### Completed ✅
- [x] EC2 instance provisioned
- [x] PostgreSQL installed and configured
- [x] FastAPI deployed with Docker
- [x] Monitoring and alerting configured
- [x] Retraining pipeline implemented

### Future Enhancements
- [ ] Set up S3 for model artifact storage
- [ ] Configure CI/CD pipeline (GitHub Actions)
- [ ] Add SSL/TLS termination for HTTPS
- [ ] Set up read replicas for database
- [ ] Implement blue-green deployment for zero-downtime updates

---

*For questions or issues, contact: karodiyamuskan2@gmail.com*
