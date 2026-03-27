# System Architecture

**FraudLens - Real-Time Fraud Detection in Digital Payments**

*Production-Grade ML System - End-to-end: Data Engineering | ML Modeling | Cloud Deployment | Production Monitoring*

---

## Table of Contents

1. [High-Level System View](#high-level-system-view)
2. [Component Architecture](#component-architecture)
3. [Data Flow Architecture](#data-flow-architecture)
4. [API Architecture](#api-architecture)
5. [Database Schema](#database-schema)
6. [Dashboard Architecture](#dashboard-architecture)
7. [Monitoring & Observability](#monitoring--observability)
8. [Retraining Pipeline](#retraining-pipeline)

---

## High-Level System View

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                    FRAUD DETECTION SYSTEM - PRODUCTION ARCHITECTURE                  │
└──────────────────────────────────────────────────────────────────────────────────────┘

┌────────────────── EXTERNAL ──────────────────┐    ┌────────────────── INTERNAL ──────────────────┐
│                                              │    │                                                │
│  ┌────────────┐    ┌────────────┐           │    │    ┌──────────────────────────────────────┐   │
│  │   Kaggle   │    │ Dashboard  │           │    │    │         MONITORING LAYER           │   │
│  │   Dataset  │    │(Streamlit) │           │    │    │  ┌─────────┐  ┌──────────────────┐   │   │
│  │            │    │  Local:8501│           │    │    │  │ PSI/KS  │──▶ Drift Detection  │   │   │
│  └─────┬──────┘    └─────┬──────┘           │    │    │  │ Tests  │   │ (28 features)     │   │   │
│        │                 │                   │    │    │  └─────────┘  └────────┬─────────┘   │   │
└────────┼─────────────────┼───────────────────┘    └────┼────────────────────────┼─────────────┘
         │                 │                             │                        │
         ▼                 ▼                             │                        ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                          INGESTION & PROCESSING LAYER                                           │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┐    │
│  │                           SCHEDULER (Cron)                                              │    │
│  │   ┌──────────────────────────────────────────────────────────────────────────────┐    │    │
│  │   │  ETL Pipeline (data_ingestion.py)                                                │    │    │
│  │   │  • Chunked processing (5000 rows/chunk)                                           │    │    │
│  │   │  • Memory-efficient for t3.medium (4GB RAM)                                      │    │    │
│  │   │  • Cron: Daily at 02:00 UTC                                                          │    │    │
│  │   └──────────────────────────────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────────────────────────────┘    │
│                                     │                                                         │
└─────────────────────────────────────┼─────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               DATA WAREHOUSE (PostgreSQL 16.13)                                 │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  Host: localhost (EC2) | Port: 5432 | Database: fraud_detection                            │
│                                                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────────────────────────┐ │
│  │ transactions_raw │  │transactions_features│ │              predictions_log                │ │
│  │   (284,807)     │  │   (engineered)    │  │              (API predictions)            │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────────────────────────┘ │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────────────────────────┐ │
│  │transactions_trn  │  │prediction_inputs│  │               alerts_log                 │ │
│  │(features+labels)│  │  (V1-V28 drift) │  │          (email alerts history)          │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────────────────────────┘ │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────────────────────────┐ │
│  │  retraining_log │  │   error_logs    │  │            pipeline_audit               │ │
│  │(retrain history)│  │  (API errors)    │  │        (ETL run history)              │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
         ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
         │   FastAPI       │  │   Streamlit     │  │   Monitoring    │
         │   Service       │  │   Dashboard     │  │   (Cron Jobs)   │
         │   Port: 8000     │  │   Port: 8501     │  │                 │
         │   Dockerized     │  │   Local only    │  │  alerting.py    │
         └─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## Component Architecture

### 1. Data Ingestion Module (`src/data_ingestion.py`)

**Purpose:** ETL pipeline for loading Kaggle dataset into PostgreSQL

**Key Features:**
- Chunked processing (5,000 rows per chunk) for memory efficiency
- Schema validation (31 columns: Time, V1-V28, Amount, Class)
- Data quality metrics (row count, fraud rate, missing values)
- Batch inserts (500 rows per database call)
- Pipeline audit logging

**Configuration:**
```python
CHUNK_SIZE = 5000      # Process 5,000 rows at a time
INSERT_BATCH_SIZE = 500  # Insert 500 rows per DB call
```

**Data Flow:**
```
creditcard.csv → validate_schema() → process_and_load_chunk() → transactions_raw
                   (31 columns)        (type conversion,     (284,807 rows)
                                         rounding)
```

---

### 2. Feature Engineering Module (`src/feature_engineering.py`)

**Purpose:** Transform raw features into model-ready inputs

**Functions:**

| Function | Input | Output |
|----------|-------|--------|
| `extract_time_features()` | `time_elapsed` | `hour`, `day`, `is_night` |
| `add_cyclic_encoding()` | `hour` | `hour_sin`, `hour_cos` |
| `scale_amount()` | `amount` | `amount_scaled` (StandardScaler) |
| `remove_correlated_features()` | features list | filtered features (|r| > 0.95) |
| `engineer_features()` | raw DataFrame | engineered DataFrame + scaler |

**Engineered Features:**
- **Time-based**: `hour` (0-23), `is_night` (0-5am flag), `hour_sin/cos` (cyclic)
- **Amount**: `amount_scaled` (StandardScaler: mean=0, std=1)
- **PCA Features**: V1-V28 (already transformed, correlation analysis applied)

---

### 3. Model Training Module (`src/model_training.py`)

**Class:** `ModelTrainer`

**Models Supported:**
1. **Logistic Regression** (baseline)
2. **Random Forest** (baseline)
3. **XGBoost** (primary model with Optuna tuning)

**Optuna Hyperparameter Tuning:**
```python
# Search Space
max_depth: 3-10
learning_rate: 0.01-0.3 (log scale)
n_estimators: 100-500
subsample: 0.6-1.0
colsample_bytree: 0.6-1.0
reg_alpha, reg_lambda: 0.0-1.0
scale_pos_weight: calculated from class ratio (~578x)

# Objective: Maximize ROC-AUC
# Trials: 100
# CV: 5-fold stratified
```

**Final Model Performance (v1.0):**
| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| ROC-AUC | 0.9814 | ≥ 0.95 | ✅ Pass |
| Precision | 0.8646 | ≥ 0.85 | ✅ Pass |
| Recall | 0.8469 | ≥ 0.90 | ⚠️ Close |
| F1-Score | 0.8557 | ≥ 0.87 | ⚠️ Close |

---

### 4. API Module (`app/`)

**File:** `app/main.py` - FastAPI Application

**Endpoints (14 total):**

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/` | None | API information |
| GET | `/api/v1/health` | None | Health check |
| GET | `/api/v1/model/info` | None | Model metadata |
| GET | `/api/v1/dashboard/stats` | None | Summary stats |
| GET | `/api/v1/dashboard/hourly` | None | Hourly statistics |
| GET | `/api/v1/dashboard/response-times` | None | Latency data |
| GET | `/api/v1/dashboard/high-risk` | None | High-risk transactions |
| GET | `/api/v1/dashboard/probability-distribution` | None | Probability histogram |
| GET | `/api/v1/dashboard/predictions/recent` | None | Recent predictions |
| GET | `/api/v1/dashboard/errors` | None | Error logs |
| POST | `/api/v1/predict` | **API Key** | Single prediction |
| POST | `/api/v1/predict/batch` | **API Key** | Batch prediction |

**API Keys:**
- `dev-key-12345` (development)
- `test-key-67890` (testing)
- From `API_KEY` env var (production)

**Middleware:**
- CORS (allow origins: localhost:3000, localhost:8501)
- Request logging (logs method, path, status, time)
- Rate limiting (60 requests/minute per key)
- Exception handlers (RFC 7807 Problem Details)

---

### 5. Model Service (`app/model.py`)

**Class:** `ModelService` (Singleton Pattern)

**Responsibilities:**
- Load model ONCE at startup (singleton)
- Thread-safe for concurrent requests
- Return predictions with risk levels (HIGH/MEDIUM/LOW)

**Input Features (31 total):**
```
[V1-V28] + [amount_scaled, hour_sin, hour_cos]
```

**Risk Levels:**
- **HIGH**: probability ≥ 0.70
- **MEDIUM**: probability ≥ 0.30
- **LOW**: probability < 0.30

---

### 6. Logging Module (`app/logging_config.py`)

**Class:** `PredictionLogger`

**Dual Logging:**
1. **File Logging** (JSONL): `logs/predictions.jsonl`, `logs/errors.jsonl`
2. **Database Logging** (PostgreSQL): `predictions_log`, `error_logs`

**Logged Per Prediction:**
- transaction_id, request data, response data
- fraud_probability, prediction, risk_level
- latency_ms, timestamp, api_key_prefix
- **Drift Monitoring**: V1-V28 features logged to `prediction_inputs` table

---

## Data Flow Architecture

### Offline Training Flow (Week 2)

```
Kaggle CSV → ETL Pipeline → PostgreSQL (transactions_raw)
  (284,807)    (Cron)            (raw data)
                                   │
                                   ▼
                          Feature Engineering
                          (hour, is_night, scaling)
                                   │
                                   ▼
                         Stratified Train/Test Split
                         (70/15/15 split)
                                   │
              ┌──────────────────┴──────────────────┐
              ▼                                     ▼
      Model Training                         Model Evaluation
      (XGBoost + Optuna)                      (ROC-AUC, PR curve)
              │
              ▼
      Model Artifact
      fraud_detector_v1.pkl (862KB)
      + metadata.json
```

### Online Inference Flow (Week 3)

```
Client Request (Dashboard/API)
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  POST /api/v1/predict                                                            │
│  {                                                                               │
│    "transaction_id": "txn_001",                                                 │
│    "amount": 150.0,                                                             │
│    "features": [31 values]  // V1-V28 + amount_scaled + hour_sin + hour_cos      │
│  }                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
                  ┌────────────────────────────────────────────────────────────┐
                  │              FastAPI Service                             │
                  │  ────────────────────────────────────────────────────────│
                  │                                                              │
                  │  1. Verify API Key (auth.py)                                  │
                  │  2. Validate Request (schemas.py)                             │
                  │  3. Model Inference (model.py)                               │
                  │  4. Calculate Risk Level                                       │
                  │  5. Log to Database + File (logging_config.py)                   │
                  │  6. Log Features for Drift (prediction_inputs)                │
                  │                                                              │
                  └──────────────────────────────────────────────────────────────┘
                                       │
                           ▼
                  ┌────────────────────────────────────────────────────────────┐
                  │  Response                                                          │
                  │  {                                                                 │
                  │    "transaction_id": "txn_001",                                       │
                  │    "fraud_probability": 0.023,                                      │
                  │    "prediction": 0,                                                  │
                  │    "risk_level": "LOW",                                             │
                  │    "threshold_used": 0.5,                                           │
                  │    "processed_at": "2026-03-26T10:30:00Z"                           │
                  │  }                                                                 │
                  └────────────────────────────────────────────────────────────┘
                                       │
                           ▼
                  ┌────────────────────────────────────────────────────────────┐
                  │  Logged to:                                                        │
                  │  • predictions_log (main table)                                  │
                  │  • prediction_inputs (V1-V28 for drift)                           │
                  │  • logs/predictions.jsonl (fallback)                               │
                  └────────────────────────────────────────────────────────────┘
```

### Monitoring & Alerting Flow (Week 4)

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                          MONITORING & ALERTING LAYER                                   │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                    CRON JOB (Every 5 minutes)                                  │ │
│  │                    src/alerting.py → run_monitoring_checks()                      │ │
│  └────────────────────────────────────────────────────────────────────────────────────┘ │
│                                          │                                          │
│  ┌──────────────────────────────────────┴──────────────────────────────────────┐   │
│  │                            MONITORING CHECKS                                │   │
│  │  ┌────────────────────────────────────────────────────────────────────────┐   │   │
│  │  │ 1. API Error Rate Check                                                       │   │   │
│  │  │    • Query: SELECT COUNT(*) FROM predictions_log WHERE predicted_at ≥ NOW-5min │   │   │
│  │  │    • Query: SELECT COUNT(*) FROM error_logs WHERE predicted_at ≥ NOW-5min   │   │   │
│  │  │    • Alert if error_rate > 1%                                                 │   │   │
│  │  └────────────────────────────────────────────────────────────────────────┘   │   │
│  │  ┌────────────────────────────────────────────────────────────────────────┐   │   │
│  │  │ 2. Latency Spike Check                                                       │   │   │
│  │  │    • Query: PERCENTILE_CONT(0.99) FROM predictions_log                   │   │   │
│  │  │    • Alert if p99 > 500ms sustained for 10 minutes                         │   │   │
│  │  └────────────────────────────────────────────────────────────────────────┘   │   │
│  │  ┌────────────────────────────────────────────────────────────────────────┐   │   │
│  │  │ 3. Model Degradation Check                                                   │   │   │
│  │  │    • Check model file age (> 30 days = warning)                            │   │   │
│  │  │    • Compare metrics vs baseline (metadata.json)                            │   │   │
│  │  └────────────────────────────────────────────────────────────────────────┘   │   │
│  └───────────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                          │
│  ┌──────────────────────────────────────┴──────────────────────────────────────┐   │
│  │                         ALERT DISPATCHER                                     │   │
│  │  ─────────────────────────────────────────────────────────────────────────────   │   │
│  │  • EmailAlerter.send_alert() → Gmail SMTP                                  │   │   │
│  │  • log_alert_to_db() → alerts_log table                                     │   │   │
│  └───────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## API Architecture

### Request/Response Flow

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                           FASTAPI SERVICE LAYERS                                     │
└──────────────────────────────────────────────────────────────────────────────────────┘

Client Request
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  1. MIDDLEWARE LAYER                                                              │
│  ────────────────────────────────────────────────────────────────────────────────│
│  • CORS Middleware: Allow origins (localhost:3000, localhost:8501)                │
│  • Request Logging: Log method, path, status, time                             │
│  • Exception Handlers: APIException, HTTPException → RFC 7807 Problem Details      │
└─────────────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  2. AUTHENTICATION LAYER (for protected endpoints)                                    │
│  ────────────────────────────────────────────────────────────────────────────────│
│  • verify_api_key: Extract X-API-Key header                                      │
│  • Validate against VALID_API_KEYS dict                                        │
│  • Return 401 Unauthorized if invalid                                             │
└─────────────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  3. VALIDATION LAYER                                                              │
│  ────────────────────────────────────────────────────────────────────────────────│
│  • Pydantic Schema Validation                                                     │
│  • PredictionRequest: transaction_id (str), amount (float, >0), features (31 floats)│
│  • Auto-generates OpenAPI docs at /docs                                          │
└─────────────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  4. BUSINESS LOGIC LAYER                                                            │
│  ────────────────────────────────────────────────────────────────────────────────│
│  • ModelService.predict()                                                        │
│  • Features: [V1-V28, amount_scaled, hour_sin, hour_cos]                          │
│  • Risk Level Classification: HIGH/MEDIUM/LOW based on probability                  │
│  • Threshold: 0.5 (default)                                                        │
└─────────────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  5. LOGGING LAYER                                                                   │
│  ────────────────────────────────────────────────────────────────────────────────│
│  • prediction_logger.log_prediction()                                           │
│  │   - PostgreSQL: predictions_log table                                         │
│  │   - File: logs/predictions.jsonl                                               │
│  │   - Drift: prediction_inputs table (V1-V28)                                  │
│  • On error: log_error() → error_logs table + logs/errors.jsonl                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
   Response to Client
```

### Dashboard Data Endpoints

**Purpose:** Feed Streamlit dashboard with real-time metrics

| Endpoint | Returns | Used By |
|----------|---------|---------|
| `/api/v1/dashboard/stats` | Total count, fraud count, fraud rate, avg probability, avg latency, risk counts | Overview page KPIs |
| `/api/v1/dashboard/hourly` | Hourly labels, volumes, fraud rates (last 24-168 hours) | Overview page trend chart |
| `/api/v1/dashboard/response-times` | Last 100 latency values (chronological) | Overview page latency chart |
| `/api/v1/dashboard/high-risk` | Last 10 HIGH risk transactions | Overview page high-risk table |
| `/api/v1/dashboard/predictions/recent` | Last 50 predictions with details | Transactions page |
| `/api/v1/dashboard/errors` | Last 20 errors from error_logs | API Health page |

---

## Database Schema

### Complete Table Listing

| Table | Purpose | Rows | Key Columns |
|-------|---------|------|-------------|
| `transactions_raw` | Raw Kaggle data | 284,807 | id, time_elapsed, v1-v28, amount, class |
| `transactions_features` | Engineered features | 284,807 | id, amount_scaled, hour, is_night, hour_sin, hour_cos |
| `transactions_training` | Features + labels for retraining | 284,807 | id, time_elapsed, v1-v28, amount, amount_scaled, hour_sin, hour_cos, class |
| `predictions_log` | API predictions | N/A | id, transaction_id, prediction, confidence, risk_level, model_version, latency_ms, predicted_at |
| `prediction_inputs` | V1-V28 for drift monitoring | N/A | transaction_id, v1-v28 |
| `error_logs` | API errors | N/A | id, endpoint, error_type, error_message, transaction_id, amount, predicted_at |
| `alerts_log` | Alert history | N/A | id, alert_type, severity, title, message, details, email_sent, created_at |
| `retraining_log` | Retraining run history | N/A | id, run_id, triggered_by, status, roc_auc, precision, recall, promoted, new_model_version |
| `pipeline_audit` | ETL run history | N/A | id, pipeline_name, started_at, completed_at, status, rows_processed |

### Schema Definitions

**transactions_raw:**
```sql
CREATE TABLE transactions_raw (
    id SERIAL PRIMARY KEY,
    time_elapsed FLOAT NOT NULL,
    v1 THROUGH v28 FLOAT NOT NULL,
    amount FLOAT NOT NULL,
    class INTEGER NOT NULL,
    ingested_at TIMESTAMP DEFAULT NOW()
);
```

**predictions_log:**
```sql
CREATE TABLE predictions_log (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(50),
    prediction INTEGER NOT NULL,
    confidence FLOAT,
    risk_level VARCHAR(10),
    model_version VARCHAR(50),
    latency_ms FLOAT,
    predicted_at TIMESTAMP DEFAULT NOW()
);
```

**alerts_log:**
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

**retraining_log:**
```sql
CREATE TABLE retraining_log (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(50) UNIQUE NOT NULL,
    triggered_by VARCHAR(50) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL,
    data_rows INTEGER,
    data_window_days INTEGER,
    roc_auc FLOAT,
    precision FLOAT,
    recall FLOAT,
    f1_score FLOAT,
    baseline_roc_auc FLOAT,
    baseline_precision FLOAT,
    baseline_recall FLOAT,
    validation_passed BOOLEAN,
    promoted BOOLEAN DEFAULT FALSE,
    new_model_version VARCHAR(50),
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Dashboard Architecture

### Streamlit Dashboard (`dashboard/`)

**Pages:**

| Page | File | Purpose |
|------|------|---------|
| Overview | `app.py` | KPI cards, fraud rate trend, high-risk transactions |
| Model Performance | `pages/1_Model_Performance.py` | Metrics, confusion matrix, probability distribution |
| Transactions | `pages/2_Transactions.py` | Live prediction testing, transaction history |
| API Health | `pages/3_API_Health.py` | Endpoint status, response times, error logs, system alerts |
| Drift Monitor | `pages/4_Drift_Monitor.py` | PSI heatmap, KS test results, feature drift table |

### Dashboard Utilities

| Module | File | Purpose |
|--------|------|---------|
| Config | `config.py` | Colors, typography, CSS, sidebar builder |
| Data Loader | `utils/data_loader.py` | PostgreSQL queries with `@st.cache_data(ttl=5)` |
| API Client | `utils/api_client.py` | HTTP client to FastAPI backend |
| Charts | `utils/charts.py` | Plotly chart builders |
| Feature Preprocessing | `utils/feature_preprocessing.py` | Feature computation helpers |

### Dashboard → API Communication

```
┌─────────────────┐                    ┌──────────────────────────────────────┐
│  Streamlit        │                    │  FastAPI Backend (EC2)                 │
│  Dashboard        │                    │  http://13.61.71.115:8000          │
│  (Local:8501)     │                    │                                      │
└─────────────────┘                    └──────────────────────────────────────┘
         │                                          │
         │  1. GET /api/v1/dashboard/stats           │
         │  2. GET /api/v1/dashboard/hourly          │
         │  3. GET /api/v1/dashboard/response-times  │
         │  4. GET /api/v1/dashboard/high-risk      │
         │  5. POST /api/v1/predict (live testing)   │
         │                                          │
         ▼                                          ▼
   Display real-time metrics                     PostgreSQL (EC2)
```

---

## Monitoring & Observability

### Drift Detection (`src/monitoring.py`)

**PSI (Population Stability Index):**
- Measures feature distribution change since training
- Bins: 10 + infinity bins
- Thresholds: < 0.1 (stable), 0.1-0.2 (warning), ≥ 0.2 (critical)

**KS Test (Kolmogorov-Smirnov):**
- Compares empirical CDFs of two samples
- p-value < 0.05 = distributions differ significantly

**Drift Metrics Computed For:**
- All 28 PCA features (V1-V28)
- Training data vs. production predictions

**Dashboard Display:**
- PSI heatmap (28 features × status colors)
- KS test results table (statistic, p-value, status)
- Feature drift table (top drifted features)

### Alerting System (`src/alerting.py`)

**Alert Types:**

| Alert Type | Threshold | Severity | Action |
|------------|-----------|----------|--------|
| API Error Rate | > 1% in 5-min window | warning/critical | Email + log |
| Latency Spike | p99 > 500ms for 10min | warning/critical | Email + log |
| Model Degradation | Age > 30 days | warning/critical | Email + log |
| Pipeline Failure | Any exception | critical | Email + log |

**Email Configuration:**
- Server: smtp.gmail.com:587
- Sender: karodiyamuskan2@gmail.com
- Recipients: karodiyamuskan2@gmail.com
- Auth: App-Specific Password

**Cron Schedule:**
```bash
*/5 * * * * cd /home/ubuntu && /usr/bin/python3 alerting.py >> /var/log/fraud_alerts.log 2>&1
```

---

## Retraining Pipeline

### Automated Retraining (`src/retraining.py`)

**Triggers:**
1. Drift detected (PSI ≥ 0.2 for ≥3 features OR KS p-value < 0.05)
2. Scheduled monthly (cron: 0 2 1 * *)
3. Manual override (`--trigger manual`)

**Pipeline Steps:**
```
1. TRIGGER → determine reason for retraining
       ↓
2. DATA → Pull from transactions_training (30-day window, max 100K rows)
       ↓
3. TRAIN → XGBoost with existing hyperparameters (from optuna_study.pkl)
       ↓
4. VALIDATE → Compare new model vs baseline (metrics must not degrade)
       ↓
5. PROMOTE → If passed: save as fraud_detector_v{N+1}.pkl
       ↓
6. DEPLOY → API loads new model on next request cycle
       ↓
7. NOTIFY → Email with metrics comparison
```

**Validation Criteria:**
| Metric | Minimum Threshold | Relative Change |
|--------|-------------------|----------------|
| ROC-AUC | ≥ 0.95 | Must not degrade |
| Recall | ≥ 0.85 | Must not degrade |
| Precision | ≥ 0.85 | Must not degrade |

**Important Note:**
- This project uses static Kaggle data (no new labeled data)
- Pipeline is implemented per project_guide.md requirements
- Production model remains v1.0 (trained on full 284,807 rows)
- Retraining can be run manually for demonstration: `python3 retraining.py --trigger manual --days 30`

---

## Deployment Architecture

### EC2 Instance (AWS)

**Instance Details:**
- **Public IP:** 13.61.71.115 (Elastic IP)
- **Region:** ap-south-1 (Mumbai)
- **Instance Type:** t3.medium (2 vCPU, 4GB RAM)
- **OS:** Ubuntu 22.04 LTS

### Docker Deployment

**Container:**
- **Name:** fraud-detection-api
- **Image:** fraud-detection-api:latest
- **Port Mapping:** 8000:8000
- **Restart Policy:** unless-stopped
- **Health Check:** curl http://localhost:8000/api/v1/health

**Docker Compose:**
```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=localhost
      - DB_PORT=5432
      - DB_NAME=fraud_detection
      - DB_USER=postgres
      - DB_PASSWORD=${DB_PASSWORD}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

### Security Groups

| Port | Protocol | Source | Purpose |
|------|----------|--------|---------|
| 22 | TCP | My IP only | SSH access |
| 8000 | TCP | 0.0.0.0/0 | FastAPI |
| 5432 | TCP | localhost | PostgreSQL (internal only) |

---

## File Organization

```
Real-Time-Fraud-Detection-in-Digital-Payments/
├── app/                          # FastAPI Application
│   ├── main.py                   # 14 endpoints, middleware
│   ├── model.py                  # ModelService singleton
│   ├── schemas.py                # Pydantic models
│   ├── config.py                 # Configuration
│   ├── auth.py                   # API key authentication
│   ├── logging_config.py         # Dual logging (JSONL + DB)
│   ├── dashboard_data.py         # Dashboard data endpoints
│   ├── rate_limit.py             # Rate limiting
│   └── exceptions.py             # Custom exceptions
│
├── dashboard/                    # Streamlit Dashboard
│   ├── app.py                    # Overview page
│   ├── config.py                 # Dashboard config
│   ├── pages/
│   │   ├── 1_Model_Performance.py
│   │   ├── 2_Transactions.py
│   │   ├── 3_API_Health.py
│   │   └── 4_Drift_Monitor.py
│   └── utils/
│       ├── data_loader.py        # PostgreSQL queries
│       ├── api_client.py         # HTTP client
│       ├── charts.py             # Plotly charts
│       └── feature_preprocessing.py
│
├── src/                          # Data Processing & Training
│   ├── config.py
│   ├── data_ingestion.py         # ETL pipeline
│   ├── feature_engineering.py    # Feature transformations
│   ├── model_training.py         # Model training
│   ├── monitoring.py             # Drift detection
│   ├── alerting.py               # Email alerting
│   ├── retraining.py             # Automated retraining
│   └── populate_training.py      # Populate training table
│
├── models/                       # Model Artifacts
│   ├── fraud_detector_v1.pkl     # Production model
│   ├── metadata.json             # Model metrics
│   └── optuna_study.pkl          # Hyperparameters
│
├── docs/                         # Documentation
│   ├── architecture.md           # This file
│   ├── infrastructure.md          # AWS/EC2 setup
│   └── monitoring_strategy.md    # Alerting & drift detection
│
├── database/                     # SQL Schemas
│   └── alerts_schema.sql
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

*Last Updated: 2026-03-27*
*Version: 1.0 - Week 4 Complete*
