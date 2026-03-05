"""
ETL Pipeline: Extract, Transform, Load for Credit Card Fraud Detection

This script:
1. Extracts data from creditcard.csv
2. Validates schema and data quality
3. Performs minimal transformations
4. Loads data into PostgreSQL transactions_raw table

Usage:
    python src/data_ingestion.py
"""
import sys
import logging
from pathlib import Path
from datetime import datetime

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from psycopg2 import sql, errors

# Import our configuration
from config import (
    BASE_DIR,
    CREDITCARD_CSV,
    DB_CONFIG,
    EXPECTED_COLUMNS,
    EXPECTED_COLUMN_COUNT,
    COLUMN_DTYPES,
)

# Configure logging (no emojis for Windows compatibility)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "logs" / "etl.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# SECTION 2: DATABASE CONNECTION
# ============================================================================

def get_db_connection():
    """
    Create a connection to the PostgreSQL database.

    Returns:
        psycopg2.connection: Database connection object

    Raises:
        Exception: If connection fails
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("Successfully connected to database")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


# ============================================================================
# SECTION 3: EXTRACT - Read CSV
# ============================================================================

def extract_data(csv_path: Path) -> pd.DataFrame:
    """
    Extract data from CSV file.

    Args:
        csv_path: Path to the CSV file

    Returns:
        pd.DataFrame: Loaded data

    Raises:
        FileNotFoundError: If CSV doesn't exist
        Exception: If reading fails
    """
    logger.info(f"Extracting data from {csv_path}")

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    # Read CSV
    df = pd.read_csv(csv_path)

    logger.info(f"Extracted {len(df)} rows, {len(df.columns)} columns")

    return df


# ============================================================================
# SECTION 4: VALIDATE - Schema & Data Quality Checks
# ============================================================================

def validate_schema(df: pd.DataFrame) -> bool:
    """
    Validate that the DataFrame has the expected schema.

    Args:
        df: DataFrame to validate

    Returns:
        bool: True if valid, raises exception if invalid

    Raises:
        ValueError: If validation fails
    """
    logger.info("Validating schema...")

    # Check 1: Column count
    if len(df.columns) != EXPECTED_COLUMN_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_COLUMN_COUNT} columns, got {len(df.columns)}"
        )

    # Check 2: Column names (exact match, case-sensitive)
    actual_columns = list(df.columns)
    if actual_columns != EXPECTED_COLUMNS:
        logger.warning(f"Column names don't match exactly.")
        logger.warning(f"Expected: {EXPECTED_COLUMNS}")
        logger.warning(f"Actual: {actual_columns}")
        # Try with case-insensitive comparison
        if [c.lower() for c in actual_columns] == [c.lower() for c in EXPECTED_COLUMNS]:
            logger.info("Columns match case-insensitively. Renaming columns...")
            df.columns = EXPECTED_COLUMNS
        else:
            raise ValueError("Column names don't match expected schema")

    # Check 3: Required columns have no nulls
    null_counts = df[EXPECTED_COLUMNS].isnull().sum()
    if null_counts.sum() > 0:
        logger.warning(f"Null values found:\n{null_counts[null_counts > 0]}")
        # For now, we'll allow nulls but log a warning

    # Check 4: Data types
    for col, expected_type in COLUMN_DTYPES.items():
        if col in df.columns:
            actual_type = str(df[col].dtype)
            if expected_type not in actual_type:
                logger.warning(
                    f"Column '{col}': expected {expected_type}, got {actual_type}"
                )
                # Try to convert
                try:
                    df[col] = df[col].astype(expected_type)
                    logger.info(f"Converted column '{col}' to {expected_type}")
                except Exception as e:
                    raise ValueError(f"Failed to convert column '{col}': {e}")

    logger.info("Schema validation passed")
    return True


def validate_data_quality(df: pd.DataFrame) -> dict:
    """
    Perform data quality checks on the DataFrame.

    Args:
        df: DataFrame to check

    Returns:
        dict: Quality metrics
    """
    logger.info("Running data quality checks...")

    metrics = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "fraud_cases": int(df["Class"].sum()),
        "legit_cases": int(len(df) - df["Class"].sum()),
        "fraud_rate": float(df["Class"].mean()),
        "missing_values": int(df.isnull().sum().sum()),
    }

    logger.info("Data Quality Metrics:")
    logger.info(f"  Total rows: {metrics['total_rows']:,}")
    logger.info(f"  Fraud cases: {metrics['fraud_cases']:,}")
    logger.info(f"  Legitimate cases: {metrics['legit_cases']:,}")
    logger.info(f"  Fraud rate: {metrics['fraud_rate']:.4%}")
    logger.info(f"  Missing values: {metrics['missing_values']}")

    # Expected: 492 fraud cases (0.172%)
    if metrics["fraud_cases"] != 492:
        logger.warning(
            f"Expected 492 fraud cases, got {metrics['fraud_cases']}"
        )

    return metrics


# ============================================================================
# SECTION 5: TRANSFORM - Apply Transformations
# ============================================================================

def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply transformations to the data.

    For now, we do minimal transformation:
    - Ensure correct data types
    - Round numerical values for cleaner database storage

    Args:
        df: Input DataFrame

    Returns:
        pd.DataFrame: Transformed DataFrame
    """
    logger.info("Applying transformations...")

    # Make a copy to avoid modifying the original
    df_transformed = df.copy()

    # Ensure Time and Amount are float
    df_transformed["Time"] = df_transformed["Time"].astype("float64")
    df_transformed["Amount"] = df_transformed["Amount"].astype("float64")

    # Round to 6 decimal places (enough precision for this use case)
    numeric_columns = df_transformed.select_dtypes(include=["float64"]).columns
    df_transformed[numeric_columns] = df_transformed[numeric_columns].round(6)

    logger.info("Transformations applied")

    return df_transformed


# ============================================================================
# SECTION 6: LOAD - Insert into Database
# ============================================================================

def load_data(conn, df: pd.DataFrame, batch_size: int = 10000) -> int:
    """
    Load data into PostgreSQL transactions_raw table.

    Uses batch INSERT for better performance.

    Args:
        conn: Database connection
        df: DataFrame to load
        batch_size: Number of rows per batch

    Returns:
        int: Number of rows inserted
    """
    logger.info(f"Loading {len(df)} rows into database...")

    cursor = conn.cursor()

    # Prepare column names for SQL query
    # Map CSV column names to database column names
    column_mapping = {
        "Time": "time_elapsed",
        "Class": "class",
    }
    # V1-V28 and Amount stay the same (lowercase)
    columns = []
    for col in EXPECTED_COLUMNS:
        if col in column_mapping:
            columns.append(column_mapping[col])
        elif col.startswith("V"):
            columns.append(col.lower())  # v1, v2, etc.
        else:
            columns.append(col.lower())  # amount

    # Build INSERT query
    table_name = "transactions_raw"
    query = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
        sql.Identifier(table_name),
        sql.SQL(", ").join(map(sql.Identifier, columns))
    )

    # Convert DataFrame to list of tuples for bulk insert
    # Get values from DataFrame using CSV column names, then map to DB schema
    data_to_insert = []
    for _, row in df.iterrows():
        values = []
        for csv_col in EXPECTED_COLUMNS:
            # Get value from DataFrame using CSV column name
            value = row[csv_col]
            # Convert numpy types to Python native types
            if hasattr(value, 'item'):  # numpy types
                value = value.item()
            elif pd.isna(value):
                value = None
            values.append(value)
        data_to_insert.append(tuple(values))

    # Batch insert
    total_inserted = 0
    for i in range(0, len(data_to_insert), batch_size):
        batch = data_to_insert[i:i + batch_size]
        try:
            execute_values(cursor, query, batch)
            conn.commit()
            total_inserted += len(batch)
            logger.info(f"  Inserted batch {i // batch_size + 1}: "
                       f"{total_inserted}/{len(df)} rows")
        except errors.UniqueViolation:
            logger.warning(f"Duplicate data detected at row {i}")
            conn.rollback()
        except Exception as e:
            logger.error(f"Error inserting batch starting at row {i}: {e}")
            conn.rollback()
            raise

    cursor.close()
    logger.info(f"Loaded {total_inserted} rows into database")

    return total_inserted


# ============================================================================
# SECTION 7: PIPELINE ORCHESTRATION
# ============================================================================

def log_pipeline_run(conn, status: str, rows_processed: int = None,
                     error_message: str = None):
    """
    Log the pipeline run to the pipeline_audit table.

    Args:
        conn: Database connection
        status: SUCCESS, FAILED, or PARTIAL
        rows_processed: Number of rows processed
        error_message: Error details if failed
    """
    cursor = conn.cursor()

    query = sql.SQL("""
        INSERT INTO pipeline_audit (pipeline_name, started_at, completed_at, status, rows_processed, error_message)
        VALUES (%s, %s, NOW(), %s, %s, %s)
    """)

    try:
        cursor.execute(query, (
            "data_ingestion_etl",
            datetime.now(),
            status,
            rows_processed,
            error_message
        ))
        conn.commit()
        cursor.close()
    except Exception as e:
        logger.error(f"Failed to log pipeline run: {e}")


def run_etl_pipeline():
    """
    Main ETL pipeline function.
    Orchestrates: Extract -> Validate -> Transform -> Load
    """
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("ETL Pipeline Started")
    logger.info("=" * 60)

    conn = None

    try:
        # 1. Connect to database
        conn = get_db_connection()

        # 2. Extract data from CSV
        df = extract_data(CREDITCARD_CSV)

        # 3. Validate schema
        validate_schema(df)

        # 4. Data quality checks
        metrics = validate_data_quality(df)

        # 5. Transform data
        df_transformed = transform_data(df)

        # 6. Load data into database
        rows_inserted = load_data(conn, df_transformed)

        # 7. Log successful run
        log_pipeline_run(conn, "SUCCESS", rows_processed=rows_inserted)

        # Summary
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info("=" * 60)
        logger.info("ETL Pipeline Completed Successfully")
        logger.info(f"   Rows processed: {rows_inserted:,}")
        logger.info(f"   Time elapsed: {elapsed:.2f} seconds")
        logger.info(f"   Throughput: {rows_inserted/elapsed:.0f} rows/sec")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"ETL Pipeline Failed: {e}")

        # Log failed run
        if conn:
            try:
                log_pipeline_run(conn, "FAILED", error_message=str(e))
            except:
                pass

        raise

    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    logs_dir = BASE_DIR / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Run the pipeline
    run_etl_pipeline()
