"""
Application Configuration

Central place for all settings - model paths, thresholds, etc.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Model Configuration
MODEL_PATH = BASE_DIR / "models" / "fraud_detector_v1.pkl"
MODEL_METADATA_PATH = BASE_DIR / "models" / "metadata.json"

# Prediction Configuration
DEFAULT_THRESHOLD = 0.5
RISK_LEVELS = {
    "HIGH": 0.7,
    "MEDIUM": 0.3,
    "LOW": 0.0
}

# API Configuration
API_TITLE = "Fraud Detection API"
API_VERSION = "1.0.0"
API_DESCRIPTION = """
Real-time fraud detection API for digital payment transactions.

## Features
- Single transaction prediction
- Batch prediction support
- Model information endpoint
- Health check for monitoring

## Risk Levels
- **HIGH**: Probability > 70% - Immediate action recommended
- **MEDIUM**: Probability 30-70% - Manual review recommended
- **LOW**: Probability < 30% - Normal processing
"""

# Feature names (expected input order)
FEATURE_NAMES = [
    'V1', 'V2', 'V3', 'V4', 'V5', 'V6', 'V7', 'V8', 'V9', 'V10',
    'V11', 'V12', 'V13', 'V14', 'V15', 'V16', 'V17', 'V18', 'V19', 'V20',
    'V21', 'V22', 'V23', 'V24', 'V25', 'V26', 'V27', 'V28',
    'amount_scaled', 'hour_sin', 'hour_cos'
]

# CORS Configuration
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8501",  # Streamlit default
]

# Database Configuration for Logging
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "fraud_detection"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# Database connection URL for SQLAlchemy
# Format: postgresql+psycopg2://user:password@host:port/database
DATABASE_URL = (
    f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

# Logging Configuration
ENABLE_DB_LOGGING = os.getenv("ENABLE_DB_LOGGING", "true").lower() == "true"
