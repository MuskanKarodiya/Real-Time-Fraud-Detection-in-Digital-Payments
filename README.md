# 🛡️ Real-Time Fraud Detection in Digital Payments

> **A Production-Grade ML System** — End-to-end fraud scoring pipeline with real-time inference at < 200ms (p99) latency.

---

## 📌 Project Overview

Financial institutions lose over **$32 billion annually** to payment fraud. Traditional rule-based systems suffer from a > 15% false positive rate, creating friction for legitimate users while still missing sophisticated fraud patterns.

This project builds a **production-grade, end-to-end ML system** that:
- Ingests transaction data via ETL pipeline and cron jobs
- Engineers features and trains an XGBoost classifier
- Serves predictions via a FastAPI endpoint deployed on AWS EC2
- Monitors system health and alerts via email and dashboard
- Tracks model drift with PSI and KS statistical tests

**Domain:** FinTech / Digital Payments

---

## 🎯 Key Performance Indicators (KPIs)

| Metric | Target | Description |
|--------|--------|-------------|
| **Precision** | ≥ 0.85 | Minimize false fraud alerts |
| **Recall** | ≥ 0.90 | Capture most real fraud instances |
| **F1-Score** | ≥ 0.87 | Balanced accuracy |
| **Latency (p99)** | < 200ms | Real-time serving requirement |
| **System Uptime** | 99.9% | High availability |
| **Model Drift** | < 0.05 | PSI threshold for retraining |

---

## 🗂️ Dataset

**Source:** [Kaggle — Credit Card Fraud Detection](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud)

| Property | Detail |
|----------|--------|
| **File** | `creditcard.csv` (stored via Git LFS) |
| **Records** | 284,807 transactions |
| **Fraud Rate** | ~0.17% (highly imbalanced) |
| **Features** | 28 PCA-transformed features + `Amount`, `Time` |
| **Target** | `Class` — 0 (legitimate), 1 (fraud) |

> ⚠️ The dataset is highly imbalanced — a core ML challenge this project addresses using SMOTE and class-weighted training in Week 2.

---

## 🏗️ System Architecture

![System Architecture](docs/architecture.png)

The system is divided into 6 layers:

| Layer | Components |
|-------|-----------|
| **1. Ingestion** | Kaggle CSV + API Feed → Airflow DAGs → PostgreSQL Raw DB |
| **2. Processing** | ETL Pipeline → Data Validation → Feature Engineering → PostgreSQL Processed DB |
| **3. Training** | XGBoost Training Module → Model Registry |
| **4. Serving** | FastAPI `/predict` → Model Inference Logic → Prediction Logs DB |
| **5. Observability** | Streamlit Dashboard + Drift/Alert Manager |
| **6. CI/CD** | GitHub Actions → Docker Build → AWS/Cloud Deploy |

---

## 🛠️ Tech Stack

| Category | Technology |
|----------|-----------|
| **Language** | Python 3.10+ |
| **ML Model** | XGBoost (hyperparameter tuned with Optuna) |
| **API** | FastAPI + Pydantic |
| **Database** | PostgreSQL (AWS EC2) |
| **Orchestration** | Cron Jobs (automated ETL and monitoring) |
| **Containerization** | Docker |
| **Cloud** | AWS EC2 (eu-north-1) |
| **Monitoring** | Custom monitoring + Gmail SMTP alerts |
| **CI/CD** | GitHub Actions |
| **Visualization** | Streamlit Dashboard |
| **Version Control** | Git + Git LFS (for large datasets) |

---

## 📁 Project Structure

> *Will be updated as the project evolves*

```
Real-Time-Fraud-Detection-in-Digital-Payments/
├── app/                          # FastAPI application
│   ├── main.py                   # API endpoints
│   ├── model.py                  # Model service
│   ├── schemas.py                # Request/response models
│   ├── logging_config.py         # Prediction & error logging
│   └── config.py                 # Configuration
├── dashboard/                    # Streamlit dashboard
│   ├── app.py                    # Overview page
│   ├── config.py                 # Dashboard config
│   ├── pages/                    # Dashboard pages
│   │   ├── 1_Model_Performance.py
│   │   ├── 2_Transactions.py
│   │   ├── 3_API_Health.py
│   │   └── 4_Drift_Monitor.py
│   └── utils/                    # Dashboard utilities
│       ├── data_loader.py        # Database queries
│       ├── charts.py             # Plotly charts
│       └── api_client.py         # API client
├── src/                          # Data processing & monitoring
│   ├── data_ingestion.py         # ETL pipeline
│   ├── feature_engineering.py    # Feature transformations
│   ├── model_training.py         # Model training
│   ├── monitoring.py             # Drift detection
│   └── alerting.py               # Alerting system
├── notebooks/                    # Jupyter notebooks
│   ├── 01_eda.ipynb              # Exploratory analysis
│   ├── 02_feature_engineering.ipynb
│   ├── 03_base_model_training.ipynb
│   ├── 04_xgboost_tuning.ipynb
│   ├── 05_class_imbalance_selection.ipynb
│   └── 06_model_card_and_evaluation.ipynb
├── models/                       # Model artifacts
│   ├── fraud_detector_v1.pkl     # Trained model
│   └── metadata.json             # Model metrics
├── database/                     # SQL schemas
│   └── alerts_schema.sql         # Alerts table schema
├── tests/                        # Test suite
│   ├── test_api.py
│   ├── test_features.py
│   └── test_model.py
├── logs/                         # Logs (gitignored)
├── Dockerfile                    # Container definition
├── docker-compose.yml            # Local development
├── requirements.txt              # Dependencies
├── .env.example                  # Environment template
├── creditcard.csv               # Dataset (Git LFS)
└── README.md
```

---

## 📈 Progress Log

| Date | Milestone |
|------|-----------|
| 2026-03-03 | Repo initialized, Git LFS configured for `creditcard.csv` |
| 2026-03-03 | Problem defined, KPIs set, dataset selected, architecture designed |
| 2026-03-06 | ETL pipeline completed, data loaded to PostgreSQL |
| 2026-03-17 | XGBoost model trained and evaluated (ROC-AUC: 0.98, Precision: 0.86, Recall: 0.85) |
| 2026-03-20 | FastAPI service built with /predict, /health, /model/info endpoints |
| 2026-03-24 | API deployed to AWS EC2 (Docker containerized) |
| 2026-03-24 | Streamlit dashboard deployed with 4 pages (Overview, Model Performance, Transactions, API Health) |
| 2026-03-25 | Drift monitoring dashboard added (PSI & KS tests for 28 features) |
| 2026-03-26 | Alerting system implemented (Gmail SMTP + cron every 5 minutes) |

## 📊 Model Performance

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **ROC-AUC** | 0.9814 | ≥ 0.95 | ✅ Pass |
| **Precision** | 0.8646 | ≥ 0.85 | ✅ Pass |
| **Recall** | 0.8469 | ≥ 0.90 | ⚠️ Close |
| **F1-Score** | 0.8557 | ≥ 0.87 | ⚠️ Close |
| **API Latency (p99)** | ~30ms | < 200ms | ✅ Pass |

## 🧪 Model Experiments

Notebooks in `notebooks/` document the model selection process:

1. **01_eda.ipynb** - Exploratory data analysis, class distribution analysis
2. **02_feature_engineering.ipynb** - Feature scaling, time-based features
3. **03_base_model_training.ipynb** - Baseline models (Logistic Regression, Random Forest)
4. **04_xgboost_tuning.ipynb** - XGBoost hyperparameter optimization with Optuna (100 trials)
5. **05_class imbalance_selection.ipynb** - Class imbalance strategies (SMOTE, class weights)
6. **06_model_card_and_evaluation.ipynb** - Final model evaluation and metrics

---

## 🚀 Live API

**Endpoint:** `http://13.61.71.115:8000/api/v1/predict` (AWS EC2)

**Example Request:**
```bash
curl -X POST "http://13.61.71.115:8000/api/v1/predict" \
  -H "X-API-Key: dev-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "txn_001",
    "amount": 150.0,
    "features": [0.0, -1.34, 0.89, ...]  # 31 features (V1-V28 + amount_scaled + hour_sin + hour_cos)
  }'
```

**Example Response:**
```json
{
  "transaction_id": "txn_001",
  "fraud_probability": 0.023,
  "prediction": 0,
  "risk_level": "LOW",
  "threshold_used": 0.5,
  "processed_at": "2026-03-26T10:30:00Z"
}
```

**API Documentation:** http://13.61.71.115:8000/docs

## 📊 Dashboard

**Local Setup:**
```bash
# Install dependencies
pip install -r requirements.txt

# Run dashboard
streamlit run dashboard/app.py
```

**Dashboard Pages:**
- **Overview** - KPI metrics, fraud rate trend, high-risk transactions
- **Model Performance** - ROC curve, confusion matrix, probability distribution
- **Transactions** - Live prediction testing, transaction history
- **API Health** - Response times, request volume, error logs
- **Drift Monitor** - PSI & KS test results for 28 features

**Monitoring:**
- Alerts configured for API error rate, latency spikes, model degradation
- Email notifications via Gmail SMTP
- Database: PostgreSQL on EC2

## 🔄 Automated Retraining Pipeline

**Status:** Implemented but not actively used (see note below)

An automated retraining pipeline (`src/retraining.py`) was implemented per project requirements with the following capabilities:

| Component | Description |
|-----------|-------------|
| **Triggers** | Drift detected, scheduled monthly, or manual override |
| **Data Source** | transactions_training table (features + labels) |
| **Validation** | New model must meet/exceed baseline metrics |
| **Promotion** | If validated, model version is incremented |
| **Notification** | Email sent with metrics comparison |

**Note on Retraining in This Project:**

This project uses a static Kaggle dataset for training. In a real production system:

- Live predictions → Fraud investigation → Labeled data → Added to training set → Model improves

In this project:

- `predictions_log` has no labels (no ground truth for live predictions)
- `transactions_raw` is static Kaggle data (never changes)
- Automated retraining would retrain on the same data without new information
- The production model (`fraud_detector_v1.pkl`) was trained on the full 284,807 rows

Therefore, the retraining pipeline exists to **demonstrate the implementation** per project requirements, but is not scheduled for automated execution. The v1 model remains the production model for all live predictions.

---

> 📝 *This README describes the deployed system and how to use it.*
