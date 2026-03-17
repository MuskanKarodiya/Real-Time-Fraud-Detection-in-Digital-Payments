# DECISIONS LOG

> This file tracks all architectural and technical decisions made during the project.
> Each decision includes context, rationale, trade-offs, and reversibility.

---

## 2026-03-05 — Decision 1: Airflow vs. Cron for Pipeline Orchestration

### Context
We are building a 4-week production-grade ML fraud detection system. The project_guide (Section 3, "Pipeline Orchestration") states:
> "Airflow DAG (or cron fallback) orchestrates the pipeline"

### Decision
**START WITH CRON, MIGRATE TO AIRFLOW IF TIME PERMITS IN WEEK 4**

### Rationale
| Factor | Cron | Airflow |
|--------|------|---------|
| Setup complexity | Simple (5 min) | Complex (1-2 hours) |
| Resource usage | Minimal | Significant (needs DB + webserver) |
| Learning curve | Basic Linux | New framework (DAGs, Operators) |
| Free tier friendly | Yes | Marginal (t2.micro may struggle) |
| Production-ready | Yes for simple pipelines | Yes for complex pipelines |
| Debugging | Logs only | UI + logs + lineage |

**Why Cron makes sense for this project:**
1. The ETL pipeline described in the guide is **linear and simple**: `ingest >> validate >> transform >> load >> quality_checks`
2. We only need **one daily run** at 02:00 UTC — cron handles this perfectly
3. As a student on free tier, Airflow's resource overhead (Postgres metadb + webserver + scheduler) could strain the t2.micro
4. You're already learning Docker, FastAPI, CI/CD, Streamlit — Airflow adds significant cognitive load in Week 1
5. The guide explicitly acknowledges "cron fallback" as acceptable

**When to consider Airflow:**
- If we finish Week 3 early and have buffer time in Week 4
- If we need multiple interdependent pipelines
- If we want advanced features (retry logic, task dependencies, UI visibility)

### Trade-offs
- **Pro (Cron):** Faster to Week 1 milestone, fewer new tools to learn, works on free tier
- **Pro (Airflow):** Better resume skill, more production features, visual pipeline monitoring
- **Mitigation:** If we switch to Airflow in Week 4, the ETL logic remains the same — we just wrap it in a DAG

### Reversible?
**Yes** — The ETL pipeline code is independent of the scheduler. Switching means wrapping existing code in an Airflow DAG definition.

### Implementation
```bash
# Week 1: Use cron
0 2 * * * cd /app && python src/data_ingestion.py >> /var/log/pipeline.log 2>&1

# Week 4 (if we switch): Wrap in Airflow DAG
# Same src/data_ingestion.py code, called via PythonOperator
```

### References
- (guide, Section 3: "Pipeline Orchestration")
- (guide, Section 6: "Infrastructure Requirements" — t2.small minimum)

---

## 2026-03-05 — Decision 2: Cloud Provider — AWS EC2 Free Tier

### Context
The project_guide (Section 6) specifies:
> "Cloud Deployment Runbook: Step-by-step deployment to AWS EC2 (adaptable to GCP/Azure)"

User is a student seeking **free options**.

### Decision
**AWS EC2 FREE TIER (t2.micro or t3.micro instance)**

### Rationale

| Option | Free Offering | Duration | Compute | Storage | Best For |
|--------|--------------|----------|---------|---------|----------|
| **AWS EC2** | 750 hrs/month | 12 months | 1 vCPU, 1GB | 30GB EBS | Students, learning |
| **GCP VM** | $300 credit | 90 days | e2-micro | 30GB | Trials |
| **Azure VM** | $200 credit | 30 days | B1s | 30GB | Trials |

**Why AWS Free Tier:**
1. **12 months vs 90 days** — Enough buffer for the full project + iterations
2. **Predictable** — No credit to track, just stay within free tier limits
3. **t2.micro/t3.micro specs** match the guide's "Minimum" column exactly
4. **Most documentation** — AWS has the most tutorials for EC2 deployment
5. **PostgreSQL included** — Can run on same instance (or use AWS RDS free tier)

### Free Tier Specifications (Our Project)
```
Instance:     t2.micro or t3.micro
vCPUs:        1
RAM:          1 GB
Storage:      8-30 GB EBS (gp2/gp3)
Hours/month:  750 (enough for 24/7 operation)
Region:       us-east-1 (N. Virginia) or other supported regions
```

### Trade-offs
- **Pro (AWS):** Full year free, most tutorials, matches guide exactly
- **Con:** Need AWS account (credit card required for verification, but not charged if free tier)
- **Mitigation:** Set up billing alerts at $1 to prevent accidental charges

### Reversible?
**No** — Migrating between clouds requires re-deploying everything. Choose AWS and stick with it.

### Setup Steps (for Week 1 Day 3)
1. Create AWS account as a student
2. Navigate to EC2 Console
3. Launch Instance → select "Free Tier eligible" filter
4. Choose Amazon Linux 2 or Ubuntu 20.04
5. Create/attach key pair for SSH access
6. Configure Security Group: allow SSH (22) and HTTP (8000)
7. Launch and note the public IP

### References
- (guide, Section 6: "Infrastructure Requirements")
- (guide, Section 6: "Cloud Deployment Runbook")

---

## 2026-03-05 — Decision 3: PostgreSQL — Self-Managed on EC2 vs. RDS

### Context
The guide specifies PostgreSQL as the database. AWS offers two options for PostgreSQL:
1. **Self-hosted** on the EC2 instance
2. **AWS RDS** (managed database service)

### Decision
**START WITH SELF-HOSTED POSTGRESQL ON EC2**

### Rationale

| Factor | Self-Hosted | RDS Free Tier |
|--------|-------------|---------------|
| Setup | One command (`yum install`) | 30+ clicks in console |
| Cost | Free (uses EC2 storage) | Free (t2.micro, 20GB) |
| Latency | Localhost (fast) | Network call |
| Learning | Learn admin skills | Managed, less learning |
| Free tier impact | Counts against EC2 only | Separate service |

**Why Self-Hosted:**
1. **Simpler setup** — One EC2 instance running both API + database
2. **Learning value** — You'll learn PostgreSQL administration (backup, restore, queries)
3. **Fewer moving parts** — One security group, one instance to manage
4. **Sufficient for this project** — Our dataset is ~200MB (284K rows × 32 columns)

### Trade-offs
- **Pro (Self-hosted):** Learn database admin, simpler architecture
- **Pro (RDS):** Automated backups, patching, scaling
- **Mitigation:** Manual backups to S3 are straightforward to add

### Reversible?
**Yes — but with effort** — Would need to export data and migrate to RDS. We'll stick with self-hosted.

### References
- (guide, Section 3: "Database Schema" — shows raw SQL DDL)
- (guide, Section 6: "Infrastructure Requirements" — lists db.t3.micro as "Minimum")

---

## 2026-03-05 — Decision 4: Project Starting Point

### Context
Current state: Repository with guide, roadmap, example repos, and creditcard.csv. No code structure yet.

### Decision
**START WEEK 1 DAY 1 IMMEDIATELY — CREATE PROJECT STRUCTURE**

### First Actions (in order):
1. Create folder structure per guide Section 11
2. Initialize Git repository with proper .gitignore
3. Set up virtual environment and requirements.txt
4. Verify creditcard.csv is accessible
5. Create DECISIONS.md (done ✓) and LEARNING_ROADMAP.md (done ✓)

### Rationale
- You want to work "rigorously" — starting now maximizes learning time
- The structure supports the entire 4-week journey
- Early decisions logged for future reference

### Next Step
Let me know when you're ready to begin Day 1 tasks!

---

*Last Updated: 2026-03-05*
