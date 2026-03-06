"""
ETL Pipeline: Extract, Transform, Load for Credit Card Fraud Detection

Memory-efficient version that processes data in chunks to work with limited RAM.
Suitable for t3.micro instances (1GB RAM).

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

# Chunk size for memory-efficient processing
CHUNK_SIZE = 5000  # Process 5,000 rows at a time
INSERT_BATCH_SIZE = 500  # Insert 500 rows per database call


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
# SECTION 3: VALIDATE SCHEMA (First chunk only)
# ============================================================================

def validate_schema_first_chunk(csv_path: Path) -> bool:
    """
    Validate schema using only the first chunk of data.
    This avoids loading the entire file into memory.

    Args:
        csv_path: Path to the CSV file

    Returns:
        bool: True if valid

    Raises:
        ValueError: If validation fails
    """
    logger.info("Validating schema (first chunk)...")

    # Read just the header to check column names
    with open(csv_path, 'r') as f:
        header_line = f.readline().strip()
        columns = header_line.split(',')

    if len(columns) != EXPECTED_COLUMN_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_COLUMN_COUNT} columns, got {len(columns)}"
        )

    if columns != EXPECTED_COLUMNS:
        logger.warning(f"Column names don't match exactly.")
        logger.warning(f"Expected: {EXPECTED_COLUMNS}")
        logger.warning(f"Actual: {columns}")

    logger.info("Schema validation passed")
    return True


def get_data_quality_metrics(csv_path: Path) -> dict:
    """
    Get data quality metrics by streaming through the file.
    Does not load the entire file into memory.

    Args:
        csv_path: Path to the CSV file

    Returns:
        dict: Quality metrics
    """
    logger.info("Calculating data quality metrics...")

    total_rows = 0
    fraud_count = 0
    missing_count = 0

    # Stream through the file to count
    for chunk in pd.read_csv(csv_path, chunksize=CHUNK_SIZE):
        total_rows += len(chunk)
        fraud_count += chunk["Class"].sum()
        missing_count += chunk.isnull().sum().sum()

    metrics = {
        "total_rows": int(total_rows),
        "total_columns": len(EXPECTED_COLUMNS),
        "fraud_cases": int(fraud_count),
        "legit_cases": int(total_rows - fraud_count),
        "fraud_rate": float(fraud_count / total_rows) if total_rows > 0 else 0,
        "missing_values": int(missing_count),
    }

    logger.info("Data Quality Metrics:")
    logger.info(f"  Total rows: {metrics['total_rows']:,}")
    logger.info(f"  Fraud cases: {metrics['fraud_cases']:,}")
    logger.info(f"  Legitimate cases: {metrics['legit_cases']:,}")
    logger.info(f"  Fraud rate: {metrics['fraud_rate']:.4%}")
    logger.info(f"  Missing values: {metrics['missing_values']}")

    if metrics["fraud_cases"] != 492:
        logger.warning(f"Expected 492 fraud cases, got {metrics['fraud_cases']}")

    return metrics


# ============================================================================
# SECTION 4: PROCESS CHUNKS AND LOAD
# ============================================================================

def process_and_load_chunk(conn, chunk: pd.DataFrame, chunk_number: int) -> int:
    """
    Transform and load a single chunk of data.

    Args:
        conn: Database connection
        chunk: DataFrame chunk to process
        chunk_number: Chunk index for logging

    Returns:
        int: Number of rows inserted
    """
    cursor = conn.cursor()

    # Transform: ensure correct types and round
    chunk = chunk.copy()
    chunk["Time"] = chunk["Time"].astype("float64")
    chunk["Amount"] = chunk["Amount"].astype("float64")

    numeric_columns = chunk.select_dtypes(include=["float64"]).columns
    chunk[numeric_columns] = chunk[numeric_columns].round(6)

    # Prepare column names for SQL query
    column_mapping = {
        "Time": "time_elapsed",
        "Class": "class",
    }

    columns = []
    for col in EXPECTED_COLUMNS:
        if col in column_mapping:
            columns.append(column_mapping[col])
        elif col.startswith("V"):
            columns.append(col.lower())
        else:
            columns.append(col.lower())

    # Build INSERT query
    table_name = "transactions_raw"
    query = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
        sql.Identifier(table_name),
        sql.SQL(", ").join(map(sql.Identifier, columns))
    )

    # Convert chunk to list of tuples
    data_to_insert = []
    for _, row in chunk.iterrows():
        values = []
        for csv_col in EXPECTED_COLUMNS:
            value = row[csv_col]
            if hasattr(value, 'item'):
                value = value.item()
            elif pd.isna(value):
                value = None
            values.append(value)
        data_to_insert.append(tuple(values))

    # Insert in smaller batches
    total_inserted = 0
    for i in range(0, len(data_to_insert), INSERT_BATCH_SIZE):
        batch = data_to_insert[i:i + INSERT_BATCH_SIZE]
        try:
            execute_values(cursor, query, batch)
            conn.commit()
            total_inserted += len(batch)
        except errors.UniqueViolation:
            logger.warning(f"Duplicate data in chunk {chunk_number}, batch {i}")
            conn.rollback()
        except Exception as e:
            logger.error(f"Error inserting chunk {chunk_number}, batch {i}: {e}")
            conn.rollback()
            raise

    cursor.close()
    return total_inserted


# ============================================================================
# SECTION 5: PIPELINE ORCHESTRATION
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
    Main ETL pipeline function with chunked processing.
    Memory-efficient: never loads the entire CSV into RAM.
    """
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("ETL Pipeline Started (Memory-Efficient Mode)")
    logger.info("=" * 60)
    logger.info(f"Chunk size: {CHUNK_SIZE:,} rows")
    logger.info(f"Insert batch size: {INSERT_BATCH_SIZE:,} rows")

    conn = None
    total_rows_inserted = 0
    chunk_count = 0

    try:
        # 1. Connect to database
        conn = get_db_connection()

        # 2. Validate schema (header only)
        validate_schema_first_chunk(CREDITCARD_CSV)

        # 3. Get data quality metrics (streaming)
        metrics = get_data_quality_metrics(CREDITCARD_CSV)

        # 4. Process and load chunks
        logger.info(f"Loading {metrics['total_rows']:,} rows in chunks of {CHUNK_SIZE:,}...")

        for chunk_index, chunk in enumerate(pd.read_csv(CREDITCARD_CSV, chunksize=CHUNK_SIZE)):
            chunk_count += 1
            rows_inserted = process_and_load_chunk(conn, chunk, chunk_index)
            total_rows_inserted += rows_inserted

            if chunk_index % 10 == 0:  # Log every 10 chunks
                logger.info(f"  Processed chunk {chunk_index + 1}: {total_rows_inserted:,}/{metrics['total_rows']:,} rows")

        # Final log
        logger.info(f"  Processed all {chunk_count} chunks: {total_rows_inserted:,} rows inserted")

        # 5. Log successful run
        log_pipeline_run(conn, "SUCCESS", rows_processed=total_rows_inserted)

        # Summary
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info("=" * 60)
        logger.info("ETL Pipeline Completed Successfully")
        logger.info(f"   Chunks processed: {chunk_count}")
        logger.info(f"   Rows processed: {total_rows_inserted:,}")
        logger.info(f"   Time elapsed: {elapsed:.2f} seconds")
        logger.info(f"   Throughput: {total_rows_inserted/elapsed:.0f} rows/sec")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"ETL Pipeline Failed: {e}")

        # Log failed run
        if conn:
            try:
                log_pipeline_run(conn, "FAILED", rows_processed=total_rows_inserted, error_message=str(e))
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
