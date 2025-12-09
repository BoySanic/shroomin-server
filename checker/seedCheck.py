import psycopg2
import psycopg2.extras
import subprocess
import re
import time
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# -------------------------
# Logging Configuration
# -------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


# Database Configuration

DB_CONFIG = {
    "dbname": os.getenv("SHROOM_DB_NAME"),
    "user": os.getenv("SHROOM_DB_USER"),
    "password": os.getenv("PGPASSWORD"),
    "host": "postgres",         # service name if running in docker-compose
    "port": 5432,
}

TABLE_NAME = os.getenv("SHROOM_SB_TABLE_NAME")
SEEDCHECK_BIN = "/checker/sizeCheck"  # path to your binary
POLL_INTERVAL = 10  # seconds between DB checks
MAX_WORKERS = os.getenv("SHROOM_CHECKER_THREADS")     # number of parallel workers

# -------------------------
# Run seedCheck
# -------------------------
def run_seedcheck(seed: int, x: int, z: int, largebiomes: bool = False):
    """
    Run the seedCheck program and return:
      - area (int) if parsed
      - elapsed time (float)
      - manual_check_needed (bool) if error message detected
    """
    cmd = [
        SEEDCHECK_BIN,
        "--worldseed", str(seed),
        "--x", str(x),
        "--z", str(z),
        "--largebiomes", str(largebiomes).lower(),
    ]

    logging.info(f"Running command: {' '.join(cmd)}")

    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running seedCheck: {e.stderr}")
        return None, 0, False

    elapsed = time.time() - start_time
    logging.info(f"seedCheck completed in {elapsed:.2f} seconds")

    stdout = result.stdout.strip()

    # Detect "mushroom island does not exist" case
    if "does not exist" in stdout or "could otherwise not be measured" in stdout:
        logging.warning("Manual check needed: " + stdout)
        return None, elapsed, True

    # Parse area
    match = re.search(r"Area:\s+(\d+)\s+square blocks", stdout)
    if match:
        return int(match.group(1)), elapsed, False
    else:
        logging.warning("Could not parse area from output:\n" + stdout)
        return None, elapsed, False

# Worker Function
def process_row(row):
    """Process a single DB row: run seedCheck, update DB, insert log."""
    row_id, seed, x, z = row["id"], row["seed"], row["x"], row["z"]
    logging.info(f"Processing row {row_id} (seed={seed}, x={x}, z={z})")

    area, elapsed, manual_needed = run_seedcheck(seed, x, z, largebiomes=False)

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    try:
        if manual_needed:
            cur.execute(
                f"UPDATE {TABLE_NAME} SET manual_check_needed = 1 WHERE id = %s",
                (row_id,),
            )
            conn.commit()
            logging.info(f"Marked row {row_id} as manual_check_needed=1")

        elif area is not None:
            cur.execute(
                f"UPDATE {TABLE_NAME} SET calculated_size = %s WHERE id = %s",
                (area, row_id),
            )
            conn.commit()
            logging.info(f"Updated row {row_id} with area={area}")

        else:
            logging.warning(f"Skipping row {row_id}, could not parse area.")
    finally:
        cur.close()
        conn.close()

    return row_id


# Main Worker Loop
def main():
    logging.info("Starting parallel seedCheck worker...")

    while True:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        try:
            # Fetch rows that need processing
            cur.execute(
                f"SELECT id, seed, x, z FROM {TABLE_NAME} WHERE calculated_size IS NULL AND (manual_check_needed = 0 or manual_check_needed is null);"
            )
            rows = cur.fetchall()

            if not rows:
                logging.info("No rows to process. Sleeping...")
                time.sleep(POLL_INTERVAL)
                continue

            logging.info(f"Found {len(rows)} rows to process. Dispatching...")

            # Process rows in parallel
            with ThreadPoolExecutor(max_workers=int(MAX_WORKERS)) as executor:
                futures = {executor.submit(process_row, row): row for row in rows}
                for future in as_completed(futures):
                    row = futures[future]
                    try:
                        row_id = future.result()
                        logging.info(f"Finished processing row {row_id}")
                    except Exception as e:
                        logging.error(f"Error processing row {row['id']}: {e}")

        finally:
            cur.close()
            conn.close()

        # Sleep before next poll
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()