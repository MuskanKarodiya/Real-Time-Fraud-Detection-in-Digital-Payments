"""
Populate transactions_training table from transactions_raw

MINIMAL CHUNK VERSION - Processes 500 rows at a time to avoid memory issues on t3.medium (4GB RAM).
"""

import logging
import os
import psycopg2
from psycopg2.extras import execute_values
import numpy as np
from sklearn.preprocessing import StandardScaler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "fraud_detection"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}


def main():
    logger.info("=" * 70)
    logger.info("     POPULATING transactions_training TABLE")
    logger.info("=" * 70)

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Clear existing data
    cursor.execute("SELECT COUNT(*) FROM transactions_training")
    existing_count = cursor.fetchone()[0]
    if existing_count > 0:
        logger.warning(f"Clearing existing {existing_count} rows")
        cursor.execute("TRUNCATE TABLE transactions_training")
        conn.commit()

    # Get total rows
    cursor.execute("SELECT COUNT(*) FROM transactions_raw")
    total_rows = cursor.fetchone()[0]
    logger.info(f"Total rows to process: {total_rows}")

    # Process in small chunks
    CHUNK_SIZE = 500
    offset = 0
    processed = 0

    # Fit scaler on first chunk
    logger.info("Fitting scaler on first chunk...")
    cursor.execute(f"SELECT amount FROM transactions_raw LIMIT {CHUNK_SIZE}")
    first_chunk = cursor.fetchall()
    amounts = [row[0] for row in first_chunk]
    scaler = StandardScaler()
    scaler.fit(np.array(amounts).reshape(-1, 1))
    logger.info("Scaler fitted")

    # Process all data in chunks
    while offset < total_rows:
        # Fetch one chunk
        logger.info(f"Fetching rows {offset} to {offset + CHUNK_SIZE}...")
        cursor.execute(f"""
            SELECT time_elapsed, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10,
                   v11, v12, v13, v14, v15, v16, v17, v18, v19, v20,
                   v21, v22, v23, v24, v25, v26, v27, v28, amount, class
            FROM transactions_raw
            ORDER BY id
            LIMIT {CHUNK_SIZE} OFFSET {offset}
        """)
        rows = cursor.fetchall()

        if not rows:
            break

        # Process this chunk
        insert_rows = []
        for row in rows:
            time_elapsed = row[0]
            v_cols = row[1:29]  # v1-v28
            amount = row[29]
            label = row[30]

            # Extract hour
            hour = int((time_elapsed / 3600) % 24)
            is_night = 1 if (hour >= 0 and hour < 5) else 0

            # Cyclic encoding
            hour_sin = float(np.sin(2 * np.pi * hour / 24))
            hour_cos = float(np.cos(2 * np.pi * hour / 24))

            # Scale amount
            amount_scaled = float(scaler.transform([[amount]])[0][0])

            insert_rows.append((
                time_elapsed, *v_cols, float(amount), amount_scaled,
                hour, hour_sin, hour_cos, is_night, label
            ))

        # Insert this chunk
        execute_values(
            cursor,
            """INSERT INTO transactions_training
               (time_elapsed, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10,
                v11, v12, v13, v14, v15, v16, v17, v18, v19, v20,
                v21, v22, v23, v24, v25, v26, v27, v28,
                amount, amount_scaled, hour, hour_sin, hour_cos, is_night, class)
               VALUES %s""",
            insert_rows
        )
        conn.commit()

        processed += len(rows)
        logger.info(f"Progress: {processed}/{total_rows} rows ({processed*100//total_rows}%)")

        # Move to next chunk
        offset += CHUNK_SIZE

    # Verify
    cursor.execute("SELECT COUNT(*) FROM transactions_training")
    final_count = cursor.fetchone()[0]

    cursor.execute("SELECT class, COUNT(*) FROM transactions_training GROUP BY class")
    label_dist = cursor.fetchall()

    logger.info("=" * 70)
    logger.info("     POPULATION COMPLETE")
    logger.info("=" * 70)
    logger.info(f"transactions_training now has {final_count} rows")
    logger.info("Label distribution:")
    for label, count in label_dist:
        label_name = "FRAUD" if label == 1 else "LEGIT"
        pct = count / final_count * 100
        logger.info(f"  {label_name}: {count} ({pct:.2f}%)")

    cursor.close()
    conn.close()
    logger.info("Database connection closed.")


if __name__ == "__main__":
    main()
