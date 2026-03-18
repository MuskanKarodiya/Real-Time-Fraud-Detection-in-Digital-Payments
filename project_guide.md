Production-Grade ML System
Design & Implementation Guide
Real-Time Fraud Detection in Digital Payments
End-to-End: Data Engineering | ML Modeling | Cloud Deployment | Production Monitoring
Technical Assessment Document | Self-Serve Engineering Guide

Document Type Technical Design & Implementation Specification
Domain FinTech / Digital Payments - Fraud Detection
Scope Full-Stack ML System: Ingestion through Production Monitoring
Tech Stack Python, FastAPI, Docker, PostgreSQL, XGBoost, Streamlit, AWS/GCP
Timeline 4-Week Sprint Execution Plan
Deliverables Live API + Dashboard + Monitoring + CI/CD Pipeline + Demo Video
How to Use This Document
This is a self-contained technical specification. Follow the sections sequentially to understand the system
design, implementation approach, deployment strategy, and acceptance criteria. All architectural decisions, code
patterns, and operational runbooks are included.
Table of Contents
1 Executive Summary & Business Context
Problem definition, business impact, success metrics
2 System Architecture
End-to-end architecture, component design, data flow
3 Data Engineering Pipeline
Ingestion, ETL, storage, data quality, schema design
4 Feature Engineering & Model Development
Feature design, model selection, training, evaluation
5 API Design & Service Layer
FastAPI service, request/response contracts, error handling
6 Containerization & Cloud Deployment
Docker, cloud infrastructure, deployment runbook
7 CI/CD Pipeline & Version Control
GitHub Actions, branching strategy, release management
8 Monitoring, Observability & Drift Detection
Performance tracking, alerting, retraining triggers
9 Dashboard & Visualization Layer
Operational dashboard, business metrics, real-time views
10 Project Execution Plan (4-Week Sprint)
Week-by-week breakdown with milestones
11 Repository Structure & Code Organization
Folder layout, naming conventions, documentation
12 Deliverables & Acceptance Criteria
Checklist, quality gates, demo requirements
13 Demo Video Script & Recording Guide
Structured walkthrough for 10-minute presentation
1. Executive Summary & Business Context
Problem Statement
Financial institutions processing digital payments face an estimated $32B+ annual loss from fraudulent

transactions globally. Current rule-based detection systems suffer from high false-positive rates (>15%) and

inability to adapt to evolving fraud patterns. This project delivers a production-grade, real-time ML-based fraud

detection system that reduces false positives while maintaining high recall on true fraud cases.

Business Objective
Build and deploy an end-to-end machine learning system capable of scoring digital payment transactions in

real-time (<200ms p99 latency), flagging potentially fraudulent activity, and providing operational visibility through

a monitoring dashboard. The system must be production-ready: containerized, CI/CD-enabled, monitored, and

designed for automated retraining.

Key Performance Indicators (KPIs)
Metric Target Rationale
Precision >= 0.85 Minimize false alerts to ops team

Recall >= 0.90 Catch maximum true fraud cases

ROC-AUC >= 0.95 Strong class separability

API Latency (p99) < 200ms Real-time scoring requirement

System Uptime >= 99.5% Production SLA compliance

False Positive Rate < 5% Reduce manual review burden

Cost Impact Analysis
At a transaction volume of 100K/day with avg. fraud value of $500, improving recall from 0.80 to 0.
recovers an estimated $5,000/day ($1.8M/year) in prevented fraud losses. Reducing false positive rate from
15% to 5% saves approximately 200 analyst-hours/month in manual review.
2. System Architecture
High-Level Architecture
The system follows a modular, event-driven architecture with clear separation between data ingestion,

processing, model serving, and observability layers. Each component is independently deployable and testable.

+------------------+ +------------------+ +-------------------+
| Data Sources | | ETL Pipeline | | Data Warehouse |
| (CSV/API/Stream)|===>| (Python/Pandas) |===>| (PostgreSQL) |
+------------------+ +------------------+ +-------------------+
||
\/
+------------------+ +------------------+ +-------------------+
| Monitoring & |<===| FastAPI Service |<===| ML Model Layer |
| Drift Detection | | (REST API) | | (XGBoost/RF) |
+------------------+ +------------------+ +-------------------+
|| || ||
\/ \/ \/
+------------------+ +------------------+ +-------------------+
| Alerting | | Dashboard | | Model Registry |
| (Logs/Email) | | (Streamlit) | | (Versioned .pkl) |
+------------------+ +------------------+ +-------------------+
Component Responsibilities
Data Ingestion Layer
Source: Kaggle Credit Card Fraud Dataset (284,807 transactions, 492 fraud cases)
Ingestion: Automated pipeline via Airflow DAG or cron-scheduled Python scripts
Format: CSV -> validated Pandas DataFrame -> PostgreSQL staging table
Frequency: Batch ingestion (configurable interval), extensible to streaming via Kafka
ETL & Processing Layer
Data validation: Schema checks, null detection, type enforcement
Cleaning: Outlier treatment, missing value imputation (median/mode strategy)
Transformation: Feature scaling (StandardScaler), encoding, time-based aggregations
Output: Clean feature table written to PostgreSQL production schema
Model Serving Layer
Framework: FastAPI with async request handling
Model loading: Singleton pattern, model loaded at startup from versioned artifact
Inference: Synchronous prediction with structured JSON response
Health check: /health endpoint for load balancer integration
Observability Layer
Prediction logging: Every inference logged with timestamp, input hash, prediction, confidence
Performance tracking: Weekly precision/recall computation against labeled feedback
Drift detection: Statistical tests (PSI, KS-test) on feature distributions
Alerting: Threshold-based alerts when metrics degrade beyond tolerance
3. Data Engineering Pipeline
Data Source & Schema
Primary dataset: Kaggle Credit Card Fraud Detection dataset containing transactions made by European

cardholders over two days in September 2013. Contains 284,807 transactions with 492 fraud cases (0.172%

positive class).

Schema Definition
Column Type Nullable Description
Time FLOAT No Seconds elapsed from first transaction

V1-V28 FLOAT No PCA-transformed features (anonymized)

Amount FLOAT No Transaction amount (USD)

Class INT No Target: 0 = legitimate, 1 = fraud

ETL Pipeline Design
Extract: Read raw CSV from data/raw/ directory or cloud storage (S3/GCS bucket)
Validate: Run schema validation, check row counts, detect anomalies in distributions
Transform: Apply StandardScaler to Amount, create time-derived features (hour_of_day, is_night)
Load: Write processed data to PostgreSQL tables (staging -> production promotion)
Audit: Log pipeline run metadata (rows processed, duration, errors) to audit table
Database Schema
CREATE TABLE transactions_raw (
id SERIAL PRIMARY KEY,
time_elapsed FLOAT NOT NULL,
v1 THROUGH v28 FLOAT NOT NULL, -- PCA components
amount FLOAT NOT NULL,
class INTEGER NOT NULL,
ingested_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE transactions_features (
id SERIAL PRIMARY KEY,
transaction_id INTEGER REFERENCES transactions_raw(id),
amount_scaled FLOAT,
hour_of_day INTEGER,
is_night BOOLEAN,
-- engineered features --
created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE predictions_log (
id SERIAL PRIMARY KEY,
transaction_id INTEGER,
prediction INTEGER,
confidence FLOAT,
model_version VARCHAR(50),
predicted_at TIMESTAMP DEFAULT NOW()
);

Pipeline Orchestration
Airflow DAG (or cron fallback) orchestrates the pipeline with the following task graph:

ingest_data >> validate_schema >> transform_features >> load_to_db >> run_quality_checks
Schedule: Daily batch run at 02:00 UTC. Retry policy: 3 retries with exponential backoff. Failure notifications via

email/Slack webhook.

4. Feature Engineering & Model Development
Feature Engineering Strategy
Raw Feature Processing
Amount: StandardScaler normalization (zero mean, unit variance)
Time: Convert to hour_of_day (cyclic encoding) and is_night_transaction flag
V1-V28: Already PCA-transformed; apply correlation analysis to remove redundant features (|r| > 0.95)
Engineered Features
Transaction velocity: Count of transactions in rolling 1h/6h/24h windows per card
Amount deviation: Z-score of current amount vs. cardholder historical mean
Time since last transaction: Seconds elapsed since previous transaction by same card
Amount percentile: Percentile rank of transaction amount within cardholder history
Night risk flag: Transactions between 00:00-05:00 local time
Class Imbalance Handling
The dataset is highly imbalanced (0.172% fraud). The following strategies are evaluated:

Technique Implementation Trade-off
SMOTE imblearn.SMOTE() Synthetic oversampling, risk of noise

Class Weights class_weight="balanced" No synthetic data, adjusts loss

Threshold Tuning Optimize on PR curve Best precision-recall control

Undersampling RandomUnderSampler Information loss, fast training

Recommended Approach
Use class_weight="balanced" during training + threshold optimization on the precision-recall curve. This
avoids synthetic data artifacts and gives direct control over the precision-recall trade-off aligned with
business cost constraints.
Model Selection & Training
Candidate Models
Model Strengths Hyperparameters Tuning Method
Logistic Reg. Interpretable, fast C, penalty, solver GridSearchCV

Random Forest Robust, handles noise n_estimators, max_depth RandomizedSearch

XGBoost Best accuracy, ranking lr, max_depth, n_rounds Optuna (Bayesian)

Training Protocol
Split: Stratified 70/15/15 (train/validation/test) preserving class distribution
Cross-validation: 5-fold stratified CV on training set for hyperparameter search
Tuning: Optuna with 100 trials for XGBoost; GridSearch for Logistic Regression
Selection: Compare models on validation set using primary metric (ROC-AUC), secondary (F1)
Final evaluation: Test set held out entirely; report all metrics with confidence intervals
Model Evaluation Framework
All models are evaluated using the following metrics matrix:

Confusion Matrix: TP, FP, TN, FN counts with visualization
ROC Curve & AUC: Model discrimination capability across all thresholds
Precision-Recall Curve: Critical for imbalanced classification performance
F1 Score: Harmonic mean at optimal threshold
Cost Matrix Analysis: Business cost of FP ($10 review) vs. FN ($500 fraud loss)
Model Artifact Management
Final model saved as versioned artifact: models/fraud_detector_v{VERSION}.pkl using joblib. Metadata
(training date, metrics, hyperparameters, data hash) stored in models/metadata.json. Model registry tracks
lineage from training data to deployed artifact.
5. API Design & Service Layer
FastAPI Service Architecture
The prediction service is built on FastAPI for its async capabilities, automatic OpenAPI documentation, and

Pydantic-based request validation. The service follows a clean layered architecture.

API Endpoints
Method Endpoint Purpose Auth
POST /api/v1/predict Score a transaction API Key

POST /api/v1/predict/batch Score multiple txns API Key

GET /api/v1/health Service health check None

GET /api/v1/model/info Model version & metrics API Key

GET /docs OpenAPI documentation None

Request/Response Contract
# POST /api/v1/predict
# Request Body:
{
"transaction_id": "TXN-2024-001",
"amount": 149.99,
"time_elapsed": 43200.0,
"features": [0.12, -1.34, 0.89, ...] // V1-V28 array
}
# Response (200 OK):
{
"transaction_id": "TXN-2024-001",
"prediction": 0,
"fraud_probability": 0.023,
"risk_level": "LOW",
"model_version": "v1.2.0",
"latency_ms": 12.
}
Error Handling
Structured error responses following RFC 7807 (Problem Details):

400 Bad Request: Invalid input schema or missing required fields
401 Unauthorized: Missing or invalid API key
422 Validation Error: Feature array length mismatch or type errors
500 Internal Server Error: Model loading failure or unexpected exception
503 Service Unavailable: Model not loaded, health check failing
Service Configuration
# app/main.py (entry point)
from fastapi import FastAPI, HTTPException
from app.model import ModelService
from app.schemas import PredictionRequest, PredictionResponse
app = FastAPI(title="Fraud Detection API", version="1.0.0")
model_service = ModelService(model_path="models/fraud_detector_v1.pkl")
@app.post("/api/v1/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
result = model_service.predict(request)
return result
@app.get("/api/v1/health")
async def health():
return {"status": "healthy", "model_loaded": model_service.is_ready()}
6. Containerization & Cloud Deployment
Docker Configuration
# Dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt.
RUN pip install --no-cache-dir -r requirements.txt
COPY..
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
CMD curl -f http://localhost:8000/api/v1/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
Cloud Deployment Runbook
Step-by-step deployment to AWS EC2 (adaptable to GCP/Azure):

Build Docker image: docker build -t fraud-detection-api:v1..
Tag for registry: docker tag fraud-detection-api:v1.0 /fraud-detection-api:v1.
Push to container registry: docker push /fraud-detection-api:v1.
Provision EC2 instance (t3.medium recommended, 4GB RAM, 2 vCPU)
Install Docker on instance, pull image, run container with port mapping (-p 8000:8000)
Configure Security Group: Allow inbound TCP 8000 from application CIDR
Validate: curl http://<public-ip>:8000/api/v1/health
Optional: Configure NGINX reverse proxy + SSL termination for production HTTPS
Infrastructure Requirements
Component Minimum Recommended Purpose
Compute t3.small (2GB) t3.medium (4GB) API + model serving

Storage 20GB EBS 50GB EBS gp3 Logs, model artifacts

Database db.t3.micro db.t3.small PostgreSQL (RDS)

Network Public subnet VPC + ALB Traffic routing

7. CI/CD Pipeline & Version Control
Branching Strategy
main ---- stable production releases (tagged v1.0, v1.1, ...)
|
+-- develop ---- integration branch, PR target
|
+-- feature/data-pipeline (Week 1)
+-- feature/model-training (Week 2)
+-- feature/api-deployment (Week 3)
+-- feature/monitoring (Week 4)
Commit Standards
Format: [module] concise description (e.g., [etl] add schema validation for raw transactions)
Frequency: Minimum 1 meaningful commit per working day
Scope: Each commit should be atomic - one logical change per commit
PR cadence: Weekly pull request from develop -> main with code review notes
Release tagging: Semantic versioning (v1.0.0, v1.1.0) after each weekly merge
GitHub Actions CI/CD Pipeline
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline
on:
push:
branches: [main, develop]
pull_request:
branches: [main]
jobs:
test:
runs-on: ubuntu-latest
steps:
uses: actions/checkout@v
uses: actions/setup-python@v
with: { python-version: "3.10" }
run: pip install -r requirements.txt
run: pytest tests/ -v --cov=src --cov-report=xml
build-and-deploy:
needs: test
if: github.ref == 'refs/heads/main'
runs-on: ubuntu-latest
steps:

uses: actions/checkout@v
run: docker build -t fraud-detection-api.
run: docker push /fraud-detection-api:latest
Testing Strategy
Unit tests: Core functions (feature engineering, prediction logic) using pytest
Integration tests: API endpoint testing with TestClient (FastAPI)
Model tests: Validate prediction output shape, value ranges, latency benchmarks
Coverage target: >= 80% on src/ module
8. Monitoring, Observability & Drift Detection
Prediction Logging
Every prediction is logged to the predictions_log table with full traceability. This enables retrospective

performance analysis and audit compliance.

Fields: transaction_id, input_hash, prediction, confidence, model_version, latency_ms, timestamp
Storage: PostgreSQL with weekly partitioning for query performance
Retention: 90 days hot storage, archived to cold storage after
Model Performance Monitoring
Weekly batch job compares model predictions against ground-truth labels (when available from fraud investigation

outcomes):

Compute precision, recall, F1, and ROC-AUC on the labeled window
Generate trend charts: metric values over rolling 4-week periods
Alert threshold: Trigger retraining if recall drops below 0.85 or precision below 0.
Data Drift Detection
Statistical monitoring of input feature distributions to detect concept drift:

Test Metric Action on Breach
PSI (Population Stability) PSI > 0.2 Flag for review, trigger retraining

KS Test (Kolmogorov-Smirnov) p-value < 0.05 Log warning, investigate feature

Mean/Std Deviation Check > 3 sigma shift Alert ops team immediately

Automated Retraining Pipeline
Trigger: Drift detected OR scheduled monthly OR manual override
Data: Pull latest 30-day window from transactions_features table
Train: Execute full training pipeline with existing hyperparameters
Validate: New model must meet or exceed current model on holdout metrics
Promote: If validated, update model artifact and increment version
Deploy: Restart API service to load new model (zero-downtime with rolling restart)
Notify: Send deployment notification with metrics comparison
Alerting Configuration
Model degradation: Precision or recall drops > 5% from baseline -> Email + Slack alert
API errors: Error rate > 1% in 5-minute window -> PagerDuty/email alert
Latency spike: p99 > 500ms sustained for 10 minutes -> Warning notification
Pipeline failure: ETL or retraining job fails -> Immediate email with error log
9. Dashboard & Visualization Layer
Streamlit Dashboard Design
The operational dashboard provides real-time visibility into system health, model performance, and business

metrics. Built with Streamlit for rapid development and deployment.

Dashboard Pages
Overview: Total transactions processed, fraud detection rate, system uptime, active model version
Model Performance: Precision/recall trend charts, confusion matrix heatmap, ROC curve
Transaction Explorer: Searchable table of recent predictions with risk scores and details
Drift Monitor: Feature distribution comparison (training vs. current), PSI values per feature
API Health: Request volume, latency percentiles, error rate time series
Key Visualizations
Time series: Fraud rate trend (daily/weekly), transaction volume over time
Distribution plots: Predicted probability histogram (fraud vs. legitimate class)
Heatmap: Confusion matrix with absolute counts and percentages
KPI cards: Real-time precision, recall, F1, AUC displayed as metric tiles
Dashboard Deployment
Streamlit app containerized alongside API or deployed separately. Accessible via public URL. Connects to same

PostgreSQL instance for prediction logs and metrics.

10. Project Execution Plan (4-Week Sprint)
Week 1: Data Foundation & Pipeline
Focus: Establish data infrastructure and automated ingestion pipeline.

Day 1-2: Define business problem, identify KPIs, select dataset, design system architecture diagram
Day 3: Set up cloud environment (VM, PostgreSQL, security groups, SSH access)
Day 4: Build ETL pipeline (extract CSV, validate schema, transform, load to PostgreSQL)
Day 5: Create Airflow DAG or cron-based scheduling for automated ingestion
Day 6-7: Perform EDA, generate statistical insights report, document data quality findings
Week 1 Milestone
Deliverables: Working ETL pipeline, populated PostgreSQL database, EDA notebook with insights,
architecture diagram. Repository initialized with proper folder structure.
Week 2: Feature Engineering & Model Training
Focus: Engineer discriminative features and train optimized models.

Day 1-2: Feature cleaning, missing value treatment, create domain-specific features
Day 3: Implement stratified train/validation/test split, set up cross-validation framework
Day 4: Train baseline models (Logistic Regression, Random Forest), evaluate performance
Day 5: Train XGBoost with Optuna hyperparameter optimization (100 trials)
Day 6: Address class imbalance, compute full evaluation metrics, select final model
Day 7: Save model artifact, document model card with metrics and training metadata
Week 2 Milestone
Deliverables: Trained model artifact (model.pkl), model evaluation report with confusion matrix, ROC curve,
PR curve, hyperparameter search results, model selection rationale document.
Week 3: Productionization & Deployment
Focus: Build production API, containerize, deploy to cloud.

Day 1-2: Build FastAPI service with /predict, /health, /model/info endpoints
Day 3: Write unit tests (pytest), integration tests for API endpoints
Day 4: Create Dockerfile, build and test container locally
Day 5: Deploy to cloud VM, configure security groups, validate public endpoint
Day 6: Set up GitHub Actions CI/CD pipeline (test -> build -> deploy)
Day 7: Build Streamlit dashboard, connect to prediction logs, deploy dashboard
Week 3 Milestone
Deliverables: Live API endpoint (public URL), Dockerized application, CI/CD pipeline running, Streamlit
dashboard deployed, test suite with >= 80% coverage.
Week 4: Monitoring, Polish & Demo
Focus: Production hardening, monitoring, documentation, demo preparation.

Day 1-2: Implement prediction logging, model performance tracking, drift detection
Day 3: Set up alerting (degradation thresholds, pipeline failure notifications)
Day 4: Implement automated retraining pipeline with validation gate
Day 5: Complete architecture documentation, monitoring strategy document
Day 6: Create demo dataset, rehearse end-to-end walkthrough, prepare demo script
Day 7: Record 10-minute demo video showing complete system operation
Week 4 Milestone
Deliverables: Monitoring dashboard with drift detection, alerting configured, retraining pipeline, complete
documentation, 10-minute demo video recording.
11. Repository Structure & Code Organization
fraud-detection-system/
|
|-- .github/
| +-- workflows/
| +-- ci-cd.yml # CI/CD pipeline definition
|
|-- data/
| |-- raw/ # Raw source data (gitignored)
| +-- processed/ # Transformed data (gitignored)
|
|-- notebooks/
| |-- 01_eda.ipynb # Exploratory data analysis
| |-- 02_feature_engineering.ipynb # Feature development
| +-- 03_model_training.ipynb # Model training & evaluation
|
|-- src/
| |-- __init__.py
| |-- data_ingestion.py # ETL pipeline logic
| |-- feature_engineering.py # Feature transformation
| |-- model_training.py # Training & evaluation
| +-- monitoring.py # Drift detection & alerting
|
|-- app/
| |-- __init__.py
| |-- main.py # FastAPI application entry
| |-- model.py # Model loading & inference
| |-- schemas.py # Pydantic request/response models
| +-- config.py # Environment configuration
|
|-- dashboard/
| +-- app.py # Streamlit dashboard
|
|-- models/
| |-- fraud_detector_v1.pkl # Trained model artifact
| +-- metadata.json # Model metadata & metrics
|
|-- tests/
| |-- test_features.py # Feature engineering tests
| |-- test_model.py # Model prediction tests
| +-- test_api.py # API endpoint tests
|
|-- docs/
| |-- architecture.md # System architecture docs
| +-- monitoring_strategy.md # Monitoring & ops runbook
|
|-- Dockerfile # Container definition
|-- docker-compose.yml # Multi-service orchestration
|-- requirements.txt # Python dependencies
|-- .env.example # Environment variable template
|-- .gitignore # Git exclusions
+-- README.md # Project overview & setup guide

Naming Conventions
Files: snake_case.py (e.g., feature_engineering.py, data_ingestion.py)
Classes: PascalCase (e.g., ModelService, PredictionRequest)
Functions: snake_case (e.g., compute_features, load_model)
Constants: UPPER_SNAKE_CASE (e.g., MODEL_PATH, API_VERSION)
Branches: feature/, fix/, release/v
Tech Stack Summary
Layer Technology Purpose
Language Python 3.10+ Core development language

ML Framework Scikit-learn, XGBoost Model training & evaluation

Data Processing Pandas, NumPy ETL & feature engineering

API Framework FastAPI + Uvicorn Model serving REST API

Database PostgreSQL Data warehouse & prediction logs

Container Docker Application packaging & deployment

Cloud AWS EC2 / GCP VM Compute infrastructure

CI/CD GitHub Actions Automated test, build, deploy

Dashboard Streamlit Operational monitoring UI

Orchestration Airflow / Cron Pipeline scheduling

12. Deliverables & Acceptance Criteria
Mandatory Deliverables
# Deliverable Description Quality Gate
1 GitHub Repository Clean structure, daily commits visible >= 20 commits

2 README Architecture diagram, setup guide, API docs Self-serve setup

3 Live API Endpoint Public URL returning predictions < 200ms latency

4 Dashboard URL Streamlit app with live metrics Publicly accessible

5 Dockerfile Containerized application Builds & runs clean

6 CI/CD Pipeline GitHub Actions workflow Green on main

7 Performance Report Metrics, curves, model comparison ROC-AUC >= 0.95

8 Monitoring Docs Drift strategy, alerting runbook Actionable ops doc

9 Demo Video 10-min end-to-end walkthrough Audio narrated

Production Acceptance Criteria
The system is considered production-ready when ALL of the following are verified:

API endpoint is publicly accessible and returns valid predictions
Dockerized application builds and runs without errors
CI/CD pipeline passes all stages (test -> build -> deploy)
Model meets target KPIs (ROC-AUC >= 0.95, Recall >= 0.90, Precision >= 0.85)
Prediction logging operational (all inferences tracked in database)
Dashboard displays real-time metrics and is publicly accessible
Monitoring and drift detection configured with alerting thresholds
Version control shows consistent daily commits with meaningful messages
Weekly release tags present (v1.0, v1.1, etc.) with changelog
Automated retraining pipeline configured and documented
Architecture documentation complete and accurate
10-minute demo video recorded with audio narration
Evaluation Dimensions
Dimension Weight What Evaluators Look For
Code Quality High Clean, modular, tested, follows conventions

System Design High Architecture clarity, component separation

ML Rigor High Proper evaluation, imbalance handling, metrics

Production Readiness High Docker, CI/CD, error handling, logging

Monitoring Medium Drift detection, alerting, retraining plan

Demo Clarity Medium Clear narration, logical flow, live proof

13. Demo Video Script & Recording Guide
Recording Requirements
Duration: 10 minutes (strict)
Format: Screen recording with audio narration (use OBS Studio, Loom, or QuickTime)
Resolution: 1080p minimum, ensure text is readable
Audio: Clear voice narration explaining each step and design decision
Output: Upload to YouTube (unlisted) or Google Drive (shared link)
Demo Script (10 Minutes)
Minutes 0-1: Introduction & Problem Context
State the problem: real-time fraud detection for digital payments
Show the architecture diagram, explain component roles
Mention the business impact and target KPIs
Minutes 1-3: Data Pipeline & Engineering
Show the ETL pipeline code and execution
Display PostgreSQL with loaded data (query sample rows)
Walk through key feature engineering logic
Show EDA notebook highlights (class distribution, feature correlations)
Minutes 3-5: Model Training & Evaluation
Show model training notebook or script execution
Display model comparison table (Logistic Regression vs. Random Forest vs. XGBoost)
Show confusion matrix, ROC curve, and precision-recall curve
Explain model selection rationale and class imbalance strategy
Minutes 5-7: Live API Demonstration
Show FastAPI /docs page (auto-generated OpenAPI documentation)
Send a sample prediction request via curl or Postman
Show the JSON response with fraud probability and risk level
Demonstrate error handling with invalid inputs
Minutes 7-8: Deployment & CI/CD
Show Dockerfile and explain the container setup
Show GitHub Actions pipeline (recent green build)
Display GitHub commit history showing daily commits
Show release tags and branching strategy
Minutes 8-10: Monitoring & Dashboard
Open the Streamlit dashboard, walk through each page
Show prediction logs in the database
Demonstrate drift detection output
Explain the retraining pipeline trigger mechanism
Close with summary: what was built, business value delivered
Demo Best Practices
Keep narration concise and technical. Avoid filler words. Pre-load all tabs and tools before recording. Use a
demo dataset designed to show both fraud and legitimate predictions. If live API is down during recording,
use a local Docker instance as fallback. Practice the full walkthrough at least twice before the final
recording.
End of Document
This document is a complete, self-contained guide for building a
production-grade ML fraud detection system.
No additional materials are required.
Good engineering is not about perfection. It is about working systems.
Questions or issues? Raise them in the GitHub repository issues tab.
All code, documentation, and artifacts should live in the repository.