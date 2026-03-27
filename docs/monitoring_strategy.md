# Monitoring Strategy & Operations Runbook

**FraudLens - Real-Time Fraud Detection System**

*Production-Grade Monitoring - Drift Detection, Alerting, Automated Retraining*

*Last Updated: 2026-03-27*

---

## Table of Contents

1. [Monitoring Overview](#monitoring-overview)
2. [Drift Detection Strategy](#drift-detection-strategy)
3. [Alerting Configuration](#alerting-configuration)
4. [Performance Monitoring](#performance-monitoring)
5. [Automated Retraining](#automated-retraining)
6. [Operational Runbook](#operational-runbook)
7. [Escalation Procedures](#escalation-procedures)

---

## Monitoring Overview

### Monitoring Objectives

1. **Detect model degradation** - Identify when model performance drops below acceptable thresholds
2. **Detect data drift** - Identify when input feature distributions change significantly
3. **Ensure system health** - Monitor API availability, latency, error rates
4. **Automate responses** - Trigger retraining when needed, send alerts to operators

### Monitoring Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                          MONITORING SYSTEM                                          │
├──────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                    CRON SCHEDULER (Every 5 minutes)                               │ │
│  │                    Command: /usr/bin/python3 alerting.py                            │ │
│  │                    Location: EC2 (/home/ubuntu/alerting.py)                            │ │
│  └────────────────────────────────────────────────────────────────────────────────────┘ │
│                                          │                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                          MONITORING CHECKS                                   │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────────┐ │ │
│  │  │ 1. Data Drift Detection (via API)                                             │ │ │
│  │  │    • PSI calculation for 28 features                                      │ │ │
│  │  │    • KS test for distribution comparison                                     │ │ │
│  │  │    • Training vs. production data                                         │ │ │ │
│  │  └─────────────────────────────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────────┐ │ │
│  │  │ 2. API Error Rate Check                                                       │ │ │
│  │  │    • Error rate = errors / total_requests                                  │ │ │
│  │  │    • Rolling 5-minute window                                                   │ │ │
│  │  │    • Threshold: > 1%                                                          │ │ │
│  │  └─────────────────────────────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────────┐ │ │
│  │  │ 3. Latency Spike Check                                                       │ │ │
│  │  │    • p99 latency from predictions_log                                       │ │ │
│  │  │    • Sustained for 10 minutes                                                 │ │
│  │  │    • Threshold: > 500ms                                                       │ │ │ │
│  │  └─────────────────────────────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────────┐ │ │
│  │  │ 4. Model Age Check                                                            │ │ │
│  │  │    • Model file age in days                                                   │ │ │
│ │  │    • Threshold: > 30 days = warning                                         │ │
│  │  └─────────────────────────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────────────────────────┘ │
│                                          │                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                         ALERT DISPATCHER                                         │ │
│  │  • EmailAlerter: Send email via Gmail SMTP                                     │ │
│  │  • log_alert_to_db: Log to alerts_log table                                   │ │
│  └─────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### Monitoring Data Sources

| Source | Table/File | Metrics |
|--------|------------|---------|
| API Predictions | `predictions_log` | Volume, fraud rate, latency, risk distribution |
| API Errors | `error_logs` | Error type, error rate, affected endpoints |
| Input Features | `prediction_inputs` | V1-V28 for drift detection |
| Training Data | `transactions_raw` | Reference distribution for drift |
| Model Metadata | `models/metadata.json` | Baseline metrics for comparison |
| Retraining History | `retraining_log` | Retraining runs, outcomes, model versions |

---

## Drift Detection Strategy

### Population Stability Index (PSI)

**Purpose:** Measure how much a feature's distribution has changed since training

**Formula:**
```
PSI = Σ[(Actual% - Expected%) × ln(Actual% / Expected%)]
```

**Interpretation:**

| PSI Value | Status | Action |
|-----------|--------|--------|
| PSI < 0.1 | Stable | No action needed |
| 0.1 ≤ PSI < 0.2 | Warning | Investigate feature |
| PSI ≥ 0.2 | Critical | Flag for review, consider retraining |

**Implementation:** `src/monitoring.py:calculate_psi()`

**Bins:** 10 equal-frequency bins + infinity bins

---

### Kolmogorov-Smirnov (KS) Test

**Purpose:** Compare empirical CDFs of two samples to detect distribution difference

**Interpretation:**

| p-value | Status | Action |
|---------|--------|--------|
| p ≥ 0.05 | Stable | Distributions are similar |
| p < 0.05 | Critical | Distributions differ significantly |

**Implementation:** `src/monitoring.py:calculate_ks_test()`

---

### Drift Monitoring Dashboard

**Page:** `dashboard/pages/4_Drift_Monitor.py`

**Features:**
1. **PSI Heatmap** - Visual representation of PSI for all 28 features
   - Green (PSI < 0.1)
   - Yellow (0.1 ≤ PSI < 0.2)
   - Red (PSI ≥ 0.2)

2. **KS Test Results Table** - Statistical test results for each feature
   - KS statistic
   - p-value
   - Status indicator

3. **Feature Drift Details** - Top drifted features with metrics

**Data Sources:**
- Training data: `transactions_raw` (reference distribution)
- Production data: `prediction_inputs` (current predictions)

---

### Drift Retraining Trigger

**Automatic Trigger Conditions:**
1. **PSI-based:** PSI ≥ 0.2 for ≥3 features
2. **KS-based:** KS test p < 0.05 for ≥3 features
3. **Combined:** 3+ features fail either test

**Manual Trigger:**
```bash
# On EC2
cd /home/ubuntu
python3 monitoring.py  # Run drift detection and check results
python3 retraining.py --trigger drift --days 30  # Manually trigger retraining
```

---

## Alerting Configuration

### Alert Types and Thresholds

| Alert Type | Threshold | Window | Severity | Action |
|------------|-----------|--------|----------|--------|
| API Error Rate | > 1% | 5-min rolling | warning (1-5%) / critical (>5%) | Email + log |
| Latency Spike | p99 > 500ms | 10-min sustained | warning (500-1000ms) / critical (>1000ms) | Email + log |
| Model Degradation | Age > 30 days | N/A | warning (30-60 days) / critical (>60 days) | Email + log |
| Pipeline Failure | Any exception | N/A | critical | Email + log |
| Drift Detected | PSI ≥ 0.2 (3+ features) | N/A | critical | Email + log + consider retrain |

### Email Configuration

**SMTP Server:** smtp.gmail.com:587

**Sender:** karodiyamuskan2@gmail.com

**Recipients:** karodiyamuskan2@gmail.com

**Authentication:** App-Specific Password (not regular password)

**Environment Variables:**
```bash
ALERT_EMAIL_ENABLED=true
ALERT_SENDER_EMAIL=<sender_email>
ALERT_SENDER_PASSWORD=<app_specific_password>
ALERT_RECIPIENTS=<recipient_emails>
```

### Email Alert Format

**Subject:** `[SEVERITY] Fraud Detection Alert: <Title>`

**Body:**
```
Alert Type: <alert_type>
Severity: <SEVERITY>
Timestamp: <ISO timestamp>

<message>

Details:
  <key1>: <value1>
  <key2>: <value2>

Recommendation: <actionable guidance>
```

### Alert Storage

**Table:** `alerts_log`

**Schema:**
```sql
CREATE TABLE alerts_log (
    id SERIAL PRIMARY KEY,
    alert_type VARCHAR(50),
    severity VARCHAR(20),
    title VARCHAR(200),
    message TEXT,
    details JSONB,
    email_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Indexes:**
- `idx_alerts_log_created_at` - For time-based queries
- `idx_alerts_log_type` - For filtering by alert type
- `idx_alerts_log_severity` - For filtering by severity

---

## Performance Monitoring

### KPI Tracking

**Metrics Dashboard:** `dashboard/pages/1_Model_Performance.py`

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| ROC-AUC | ≥ 0.95 | 0.9814 | ✅ Pass |
| Precision | ≥ 0.85 | 0.8646 | ✅ Pass |
| Recall | ≥ 0.90 | 0.8469 | ⚠️ Close |
| F1-Score | ≥ 0.87 | 0.8557 | ⚠️ Close |
| API Latency (p99) | < 200ms | ~30ms | ✅ Pass |

### API Performance Monitoring

**Endpoint:** `/api/v1/dashboard/response-times`

**Metrics:**
- p50 latency
- p90 latency
- p99 latency
- Average latency

**Dashboard:** `dashboard/pages/3_API_Health.py`

### Prediction Volume Monitoring

**Endpoint:** `/api/v1/dashboard/hourly`

**Metrics:**
- Transaction volume per hour
- Fraud rate per hour
- Trend analysis (48-hour view)

**Dashboard:** `dashboard/pages/app.py` (Overview page)

---

## Automated Retraining

### Retraining Triggers

| Trigger | Description |
|---------|-------------|
| **Drift Detected** | Automatic: PSI ≥ 0.2 for 3+ features OR KS p-value < 0.05 for 3+ features |
| **Scheduled** | Cron: Monthly (1st of every month at 2 AM UTC) - **NOT ACTIVE** (static dataset) |
| **Manual** | CLI: `python3 retraining.py --trigger manual --days 30` |

### Retraining Pipeline

**File:** `src/retraining.py` (~1050 lines)

**Steps:**

1. **Trigger** → Determine reason for retraining
2. **Data** → Pull from `transactions_training` (30-day window, max 100K rows)
3. **Train** → XGBoost with existing hyperparameters (from `optuna_study.pkl`)
4. **Validate** → Compare new model vs baseline on test set
5. **Promote** → If validated: save as `fraud_detector_v{N+1}.pkl`
6. **Deploy** → API loads new model on next request (zero-downtime)
7. **Notify** → Email with metrics comparison

### Validation Criteria

| Metric | Minimum Threshold | Relative Change |
|--------|-------------------|----------------|
| ROC-AUC | ≥ 0.95 | Must not degrade |
| Recall | ≥ 0.85 | Must not degrade |
| Precision | ≥ 0.85 | Must not degrade |

**Decision Logic:**
```python
if all_metrics_meet_minimum AND avg_change >= 0:
    PROMOTE to production
else:
    REJECT - keep current model
```

### Retraining CLI

**Usage:**
```bash
# Manual retraining with 30-day data window
python3 retraining.py --trigger manual --days 30

# Scheduled retraining (for cron)
python3 retraining.py --trigger scheduled --days 30

# Drift-triggered retraining
python3 retraining.py --trigger drift --days 30

# Force promotion (skip validation)
python3 retraining.py --trigger manual --days 30 --force
```

### Retraining History

**Table:** `retraining_log`

**Columns:**
- `run_id` - Unique identifier (e.g., `retrain_20260326_092038`)
- `triggered_by` - 'drift', 'scheduled', or 'manual'
- `started_at`, `completed_at` - Timestamps
- `status` - 'running', 'completed', 'failed', 'rejected'
- `roc_auc`, `precision`, `recall`, `f1_score` - New model metrics
- `baseline_*` - Current model metrics for comparison
- `validation_passed` - Boolean validation result
- `promoted` - Whether model was promoted to production
- `new_model_version` - Version if promoted (e.g., `fraud_detector_v2`)

**View Retraining History:**
```sql
SELECT * FROM retraining_log ORDER BY started_at DESC LIMIT 10;
```

---

## Operational Runbook

### Daily Operations

**Check:**
- [ ] API health: `curl http://13.61.71.115:8000/api/v1/health`
- [ ] Dashboard accessible: `http://localhost:8501`
- [ ] Recent predictions logged: `SELECT COUNT(*) FROM predictions_log WHERE predicted_at > NOW() - INTERVAL '1 hour';`

**Commands:**
```bash
# API health check
curl http://13.61.71.115:8000/api/v1/health

# Check recent predictions
sudo -u postgres psql -d fraud_detection -c "SELECT COUNT(*) FROM predictions_log WHERE predicted_at > NOW() - INTERVAL '1 hour';"

# Check alerts in last 24 hours
sudo -u postgres psql -d fraud_detection -c "SELECT * FROM alerts_log WHERE created_at > NOW() - INTERVAL '1 day' ORDER BY created_at DESC LIMIT 10;"

# View monitoring logs
tail -f /var/log/fraud_alerts.log
```

### Weekly Operations

**Check:**
- [ ] Drift detection dashboard for critical features
- [ ] API latency trends (any p99 > 100ms?)
- [ ] Error rate trends (any increase?)
- [ ] Model age (is retraining needed?)

**Commands:**
```bash
# Check drift metrics via API
curl http://13.61.71.115:8000/api/v1/dashboard/drift

# Check model age
ls -lh /home/ubuntu/models/fraud_detector_v1.pkl

# Review recent alerts
sudo -u postgres psql -d fraud_detection -c "SELECT alert_type, severity, title, created_at FROM alerts_log WHERE created_at > NOW() - INTERVAL '7 days' ORDER BY created_at DESC;"
```

### Monthly Operations

**Check:**
- [ ] Review retraining history
- [ ] Compare current vs. baseline metrics
- [ ] Verify email alerts are working
- [ ] Check disk space usage

**Commands:**
```bash
# Disk space
df -h

# Database size
sudo -u postgres psql -d fraud_detection -c "SELECT pg_size_pretty(pg_database_size('fraud_detection'));"

# Table sizes
sudo -u postgres psql -d fraud_detection -c "\dt+ transactions_*"

# Send test alert
python3 -c "from src.alerting import EmailAlerter; e=EmailAlerter(); e.send_alert('test', 'info', 'Test Alert', 'This is a test')"

# Backup database
sudo -u postgres pg_dump -d fraud_detection > backup_$(date +%Y%m%d).sql
```

---

## Escalation Procedures

### Severity Levels

| Severity | Condition | Response Time | Escalation |
|----------|-----------|----------------|------------|
| **Info** | Normal operation | None | None |
| **Warning** | Degraded but functional | 1 business day | Monitor closely |
| **Critical** | Service impacted | 1 hour | Page on-call |

### Critical Alert Procedures

#### 1. API Down

**Symptoms:**
- Health check returns 503
- API not responding to requests

**Steps:**
```bash
# 1. Check container status
docker ps | grep fraud-detection-api

# 2. Check container logs
docker logs --tail 50 fraud-detection-api

# 3. Restart container if needed
docker restart fraud-detection-api

# 4. If restart fails, rebuild and redeploy
cd /home/ubuntu
docker stop fraud-detection-api
docker rm fraud-detection-api
docker build -t fraud-detection-api:latest .
docker run -d --name fraud-detection-api -p 8000:8000 --restart unless-stopped fraud-detection-api:latest
```

#### 2. Database Down

**Symptoms:**
- API returns 500 with "database connection failed"
- Cannot connect via psql

**Steps:**
```bash
# 1. Check PostgreSQL status
sudo systemctl status postgresql

# 2. Start PostgreSQL if stopped
sudo systemctl start postgresql

# 3. Check if port is listening
sudo netstat -tulpn | grep 5432

# 4. View error logs
sudo journalctl -u postgres -xe
```

#### 3. High Error Rate (> 1%)

**Symptoms:**
- Many error entries in `error_logs`
- Alert email received

**Steps:**
```bash
# 1. Check recent errors
sudo -u postgres psql -d fraud_detection -c "SELECT endpoint, error_type, COUNT(*) FROM error_logs WHERE predicted_at > NOW() - INTERVAL '1 hour' GROUP BY endpoint ORDER BY count DESC;"

# 2. Check API logs for specific errors
tail -f /var/log/fraud_alerts.log

# 3. Common issues:
#    - Invalid input format → Check request schema
#    - Model not loaded → Check model service logs
#    - Database connection → Check database status
```

#### 4. Model Drift Detected

**Symptoms:**
- Alert email: "Data Drift Detected - X Features Affected"
- Dashboard shows red features

**Steps:**
```bash
# 1. Check drift details
sudo -u postgres psql -d fraud_detection -c "SELECT * FROM alerts_log WHERE alert_type='data_drift' ORDER BY created_at DESC LIMIT 1;"

# 2. View drift metrics on dashboard
# Open: http://localhost:8501 and go to Drift Monitor page

# 3. Decision: Retrain or investigate?
#    - Investigate first: Check if data quality issue or real drift
#    - If real drift: Run retraining
python3 retraining.py --trigger drift --days 30

# 4. Monitor retraining
sudo -u postgres psql -d fraud_detection -c "SELECT * FROM retraining_log ORDER BY started_at DESC LIMIT 1;"
```

#### 5. Latency Spike (> 500ms p99)

**Symptoms:**
- Alert email: "Latency Spike Detected: p99 = XXXms"
- Dashboard shows increased latency

**Steps:**
```bash
# 1. Check resource usage
htop

# 2. Check recent latencies
sudo -u postgres psql -d fraud_detection -c "SELECT latency_ms, predicted_at FROM predictions_log WHERE latency_ms IS NOT NULL ORDER BY predicted_at DESC LIMIT 20;"

# 3. Possible causes:
#    - Database connection pool exhausted → Check connection count
#    - High request volume → Check if traffic spike
#    - Model loading overhead → Should be singleton (check model.py)

# 4. If database is bottleneck:
#    - Add connection pooling (pgbouncer)
#    - Increase database instance size

# 5. If traffic spike:
#    - Consider auto-scaling (multiple API instances)
#    - Implement rate limiting more aggressively
```

---

## Alert Silence Procedures

### Temporary Alert Silence (Emergency Only)

**Use Case:** Planned maintenance, known issues being resolved

**Method:**

```bash
# SSH to EC2
ssh -i "C:/Users/Dell/Downloads/fraud-detection-key.pem" ubuntu@13.61.71.115

# Comment out cron job temporarily
crontab -e
# */5 * * * * cd /home/ubuntu && /usr/bin/python3 alerting.py >> /var/log/fraud_alerts.log 2>&1
# Change to:
# */5 * * * * cd /home/ubuntu && /usr/bin/python3 alerting.py >> /var/log/fraud_alerts.log 2>&1

# Save and exit (enter on empty line to save)

# To re-enable:
crontab -e
# Uncomment the line above
```

---

## Monitoring File Locations

| File | Location | Purpose |
|------|----------|---------|
| Alert logs | `/var/log/fraud_alerts.log` | Cron job output |
| Prediction logs | `logs/predictions.jsonl` | Fallback API logs (local) |
| Error logs | `logs/errors.jsonl` | Fallback error logs (local) |
| Database logs | PostgreSQL journal | Database operations |
| Retraining logs | `retraining_log` table | Retraining history |

---

## Contact Information

**System Owner:** karodiyamuskan2@gmail.com

**Escalation:** See Escalation Procedures section above

**Documentation:**
- `docs/architecture.md` - System architecture
- `docs/infrastructure.md` - Infrastructure details (this file)
- `docs/monitoring_strategy.md` - This document

---

*For monitoring questions or system issues, email: karodiyamuskan2@gmail.com*
