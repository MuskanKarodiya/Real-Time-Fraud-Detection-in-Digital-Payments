# Learning Roadmap — Real-Time Fraud Detection System

> **Your Background:** Python, Basic ML, SQL, Git — No Docker/FastAPI/CI/CD experience
>
> **Goal:** Complete production-grade ML system in 4 weeks

---

## 📊 Self-Assessment (Update as you progress)

| Skill | Current Level (1-10) | Target Level |
|-------|---------------------|--------------|
| Python | ? | 7 |
| SQL | ? | 6 |
| Git | ? | 6 |
| ML Concepts | ? (Basic) | 7 |
| Docker | 1 | 6 |
| FastAPI | 1 | 6 |
| CI/CD | 1 | 5 |
| Cloud/AWS | 1 | 5 |

---

## 🎯 Prerequisites (Complete Before Week 1 Day 1)

### 1. Docker Fundamentals (~4 hours)
**Why:** You'll containerize the entire application in Week 3.

- 📺 **YouTube:** "Docker Tutorial for Beginners" by Programming with Mosh (1 hour)
  - Focus on: Images, Containers, Dockerfile, Docker Compose
- 📄 **Official:** https://docs.docker.com/get-started/
- 📝 **Practice:** Build a simple "Hello World" Python container

**Checkpoint:** Can you explain the difference between an image and a container?

---

### 2. FastAPI Basics (~3 hours)
**Why:** Week 3 requires building a REST API service.

- 📺 **YouTube:** "FastAPI in 100 Seconds" ( Fireship) + "FastAPI Tutorial" (ArjanCodes)
- 📄 **Official:** https://fastapi.tiangolo.com/tutorial/
- 📝 **Practice:** Build a simple endpoint that returns `{"status": "healthy"}`

**Checkpoint:** Can you start a FastAPI server and access the auto-generated `/docs` page?

---

### 3. GitHub Actions Basics (~2 hours)
**Why:** Week 3 requires setting up CI/CD pipeline.

- 📺 **YouTube:** "GitHub Actions Tutorial for Beginners" (Traversy Media)
- 📄 **Official:** https://docs.github.com/actions/get-started
- 📝 **Practice:** Create a simple workflow that runs `echo "Hello"` on push

**Checkpoint:** Can you trigger a GitHub Action by pushing code?

---

## 📅 Week 1 — Data Foundation & Pipeline

### Day 1-2: Project Setup & Architecture
**Focus:** Understanding the problem and setting up the codebase.

**Learn:**
- 📺 **YouTube:** "System Design for ML Projects" (search)
- 📄 **Read:** project_guide.md Section 1 & 2
- 📝 **Activity:** Draw the architecture diagram on paper/whiteboard

### Day 3: Cloud Setup (AWS EC2 Free Tier)
**Focus:** Setting up a free cloud server.

**Learn:**
- 📺 **YouTube:** "AWS EC2 Free Tier Tutorial" (NetworkChuck or freeCodeCamp)
- 📄 **AWS Docs:** https://docs.aws.amazon.com/ec2/
- 📝 **Practice:** Launch a free tier t2.micro instance

**Free Tier Details:**
- AWS offers 12 months free tier for students
- 750 hours/month of t2.micro or t3.micro
- Perfect for our project's needs

### Day 4: PostgreSQL on Cloud
**Focus:** Setting up database on the cloud VM.

**Learn:**
- 📺 **YouTube:** "PostgreSQL on AWS EC2" (search)
- 📄 **Docs:** https://www.postgresql.org/docs/
- 📝 **Practice:** Install PostgreSQL, create database, connect remotely

### Day 5: **Airflow vs Cron Decision**
**See Decision Section Below — We recommend Airflow for this project**

**Learn (if Airflow):**
- 📺 **YouTube:** "Apache Airflow Tutorial for Beginners" (Marcos Iglesias)
- 📄 **Docs:** https://airflow.apache.org/docs/
- 📝 **Practice:** Set up a simple DAG with 2 tasks

**Learn (if Cron fallback):**
- 📺 **YouTube:** "Linux Cron Job Tutorial" (Tech with Tim)
- 📄 **Docs:** `man crontab` in terminal
- 📝 **Practice:** Schedule a Python script to run daily

### Day 6-7: Exploratory Data Analysis (EDA)
**Focus:** Understanding the Kaggle Credit Card dataset.

**Learn:**
- 📺 **YouTube:** "EDA with Python" (Keith Galli or StatQuest)
- 📄 **Pandas Docs:** https://pandas.pydata.org/docs/user_guide/
- 📝 **Activity:** Recreate analysis from notebooks in `Example_Repos_To_Refer/`

---

## 📅 Week 2 — Feature Engineering & Model Training

### Day 1-2: Feature Engineering
**Focus:** Creating useful features from raw data.

**Learn:**
- 📺 **YouTube:** "Feature Engineering Tutorial" (search)
- 📄 **Scikit-learn:** https://scikit-learn.org/stable/user_guide.html
- 📝 **Read:** project_guide.md Section 4

**Key Concepts to Master:**
- StandardScaler (for `Amount` column)
- Cyclic encoding (for `Time` → hour_of_day)
- Class imbalance handling

### Day 3: Train/Test Split & Cross-Validation
**Focus:** Properly splitting data for ML.

**Learn:**
- 📺 **YouTube:** "Cross Validation Explained" (StatQuest with Josh Starmer)
- 📄 **Docs:** https://scikit-learn.org/stable/modules/cross_validation.html
- 📝 **Practice:** Implement stratified K-fold

### Day 4: Baseline Models
**Focus:** Logistic Regression & Random Forest.

**Learn:**
- 📺 **YouTube:** "Logistic Regression" + "Random Forest" (StatQuest)
- 📄 **Docs:** https://scikit-learn.org/stable/user_guide.html
- 📝 **Reference:** `Example_Repos_To_Refer/AI-Based-Fraud-Detection-main/MachineLearningModels.py`

### Day 5: XGBoost + Optuna
**Focus:** Advanced model with hyperparameter tuning.

**Learn:**
- 📺 **YouTube:** "XGBoost Explained" (StatQuest)
- 📺 **YouTube:** "Optuna Tutorial" (search)
- 📄 **Docs:** https://xgboost.readthedocs.io/ + https://optuna.org/
- 📝 **Practice:** Run 20-50 Optuna trials (not full 100 to save time)

### Day 6-7: Model Evaluation & Selection
**Focus:** Comparing models and selecting the winner.

**Learn:**
- 📺 **YouTube:** "ROC Curve & AUC" (StatQuest)
- 📄 **Read:** project_guide.md Section 4 — "Model Evaluation Framework"
- 📝 **Practice:** Generate confusion matrix, ROC curve, PR curve

---

## 📅 Week 3 — Productionization & Deployment

### Day 1-2: FastAPI Service
**Focus:** Building the prediction API.

**Learn:**
- 📺 **YouTube:** "Production FastAPI" (ArjanCodes)
- 📄 **Reference:** `Example_Repos_To_Refer/Three-Model-Deep-Learning-Fraud-Detection-System-main/app.py`
- 📄 **Docs:** https://fastapi.tiangolo.com/tutorial/
- 📝 **Practice:** Implement `/predict`, `/health`, `/model/info` endpoints

### Day 3: Testing with Pytest
**Focus:** Writing unit and integration tests.

**Learn:**
- 📺 **YouTube:** "Pytest Tutorial" (ArjanCodes)
- 📄 **Docs:** https://docs.pytest.org/
- 📝 **Practice:** Write tests for each endpoint

### Day 4: Docker Containerization
**Focus:** Packaging the application.

**Learn:**
- 📺 **YouTube:** "Docker for Python Apps" (search)
- 📄 **Reference:** project_guide.md Section 6 — Dockerfile example
- 📝 **Practice:** Build and test the container locally

### Day 5: Cloud Deployment
**Focus:** Deploying container to AWS EC2.

**Learn:**
- 📺 **YouTube:** "Deploy Docker to AWS EC2" (Tech World with Nana)
- 📄 **Read:** project_guide.md Section 6 — "Cloud Deployment Runbook"
- 📝 **Practice:** Deploy your container, test the public endpoint

### Day 6: CI/CD Pipeline
**Focus:** Automating test, build, deploy.

**Learn:**
- 📺 **YouTube:** "Complete CI/CD Pipeline" (freeCodeCamp)
- 📄 **Read:** project_guide.md Section 7
- 📝 **Practice:** Set up GitHub Actions workflow

### Day 7: Streamlit Dashboard
**Focus:** Building monitoring UI.

**Learn:**
- 📺 **YouTube:** "Streamlit Tutorial" (search)
- 📄 **Reference:** `Example_Repos_To_Refer/online-payment-fraud-detection-app-main/streamlit_app.py`
- 📄 **Docs:** https://docs.streamlit.io/
- 📝 **Practice:** Build Overview and Model Performance pages

---

## 📅 Week 4 — Monitoring, Polish & Demo

### Day 1-2: Prediction Logging & Drift Detection
**Focus:** Monitoring model health.

**Learn:**
- 📺 **YouTube:** "Model Drift Detection" (search)
- 📄 **Read:** project_guide.md Section 8
- 📝 **Concepts to understand:** PSI, KS test, mean/standard deviation checks

### Day 3: Alerting
**Focus:** Getting notified when things break.

**Learn:**
- 📺 **YouTube:** "Alerting Best Practices" (search)
- 📄 **Read:** project_guide.md Section 8 — "Alerting Configuration"
- 📝 **Practice:** Set up email alerts for test failures

### Day 4: Automated Retraining
**Focus:** Pipeline to retrain the model automatically.

**Learn:**
- 📄 **Read:** project_guide.md Section 8 — "Automated Retraining Pipeline"
- 📝 **Practice:** Create a script that retrains when drift is detected

### Day 5: Documentation
**Focus:** Completing architecture and ops docs.

**Learn:**
- 📄 **Read:** project_guide.md Section 11 & 12
- 📝 **Practice:** Write your own architecture.md based on what you built

### Day 6: Demo Preparation
**Focus:** Preparing for the recording.

**Learn:**
- 📄 **Read:** project_guide.md Section 13 — Demo Script
- 📝 **Practice:** Do 2-3 dry runs of the full walkthrough

### Day 7: Demo Recording
**Focus:** Recording the 10-minute video.

**Tools:**
- OBS Studio (free, open source)
- Loom (free tier available)
- Or built-in screen recording

---

## 🎓 Free Learning Resources Summary

| Topic | Best Free Resource |
|-------|-------------------|
| Docker | Programming with Mosh (YouTube) |
| FastAPI | Official docs + ArjanCodes (YouTube) |
| GitHub Actions | Traversy Media (YouTube) |
| AWS EC2 | NetworkChuck (YouTube) |
| PostgreSQL | PostgreSQL Tutorial (YouTube) |
| Airflow | Marcos Iglesias (YouTube) |
| XGBoost | StatQuest with Josh Starmer (YouTube) |
| Optuna | Official documentation |
| Streamlit | Official documentation |
| Testing | ArjanCodes (YouTube) |

---

## ✅ Daily Learning Checklist

Before each coding session:

- [ ] Did I watch the recommended videos for this week's topics?
- [ ] Did I read the relevant section from project_guide.md?
- [ ] Do I understand WHAT we're building today?
- [ ] Do I understand WHY we're doing it this way?

---

## 📝 Notes

- **Estimated total learning time:** 40-60 hours before starting + 5-10 hours/week during project
- **Best approach:** Learn a bit, then apply immediately — don't binge all videos first
- **When stuck:** Re-watch at 1.5x speed focusing on the specific part you need
- **Take notes:** Write down concepts in your own words in a NOTES.md file

---

*Last Updated: 2026-03-05*
