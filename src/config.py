"""
Configuration file for the Fraud Detection System.

This file stores environment-specific settings like database credentials,
file paths, and other configuration values.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Data directories
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Database configuration
# For local development (running on your laptop)
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "fraud_detection"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# For remote database (EC2), set this environment variable:
# export DB_HOST=13.61.71.115 (on EC2, it's localhost)

# File paths
CREDITCARD_CSV = RAW_DATA_DIR / "creditcard.csv"

# ETL Configuration
EXPECTED_COLUMNS = [
    "Time", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9", "V10",
    "V11", "V12", "V13", "V14", "V15", "V16", "V17", "V18", "V19", "V20",
    "V21", "V22", "V23", "V24", "V25", "V26", "V27", "V28", "Amount", "Class"
]

EXPECTED_COLUMN_COUNT = 31

# Schema: column name -> data type
COLUMN_DTYPES = {
    "Time": "float64",
    "Amount": "float64",
    "Class": "int64",
}
# V1-V28 are all float, handled in validation

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
