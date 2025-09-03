from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List
import psycopg2
import psycopg2.extras
import os

# -------------------------
# Database Configuration
# -------------------------
DB_CONFIG = {
    "dbname": os.getenv("SHROOM_DB_NAME"),
    "user": os.getenv("SHROOM_DB_USER"),
    "password": os.getenv("PGPASSWORD"),
    "host": "postgres", #Leave alone if you're on docker, change if not
    "port": 5432,
}

TABLE_NAME = os.getenv("SHROOM_TABLE_NAME")

# FastAPI App

app = FastAPI()


# Pydantic Models

class SeedEntry(BaseModel):
    seed: int
    x: int
    z: int
    claimed_size: int

class Payload(BaseModel):
    data: List[SeedEntry]


# Database Helper

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

# API Endpoint

@app.post("/endpoint")
async def receive_payload(payload: Payload, request: Request):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    try:
        for entry in payload.data:
            # 1. Check for exact match
            cur.execute(
                f"""
                SELECT * FROM {TABLE_NAME}
                WHERE seed = %s AND x = %s AND z = %s AND claimed_size = %s
                """,
                (entry.seed, entry.x, entry.z, entry.claimed_size),
            )
            exact_match = cur.fetchone()

            if exact_match:
                # Exact match found → reject
                raise HTTPException(
                    status_code=409,
                    detail=f"Exact match already exists for seed {entry.seed}",
                )

            # 2. Check for seed-only match
            cur.execute(
                f"""
                SELECT * FROM {TABLE_NAME}
                WHERE seed = %s
                """,
                (entry.seed,),
            )
            seed_match = cur.fetchone()

            if seed_match:
                # Insert new row with flag = 1
                cur.execute(
                    f"""
                    INSERT INTO {TABLE_NAME} (seed, x, z, claimed_size, duplicate_seed_flag)
                    VALUES (%s, %s, %s, %s, 1)
                    RETURNING id
                    """,
                    (entry.seed, entry.x, entry.z, entry.claimed_size),
                )
                conn.commit()
                continue

            # 3. No match at all → insert normally with flag = 0
            cur.execute(
                f"""
                INSERT INTO {TABLE_NAME} (seed, x, z, claimed_size, duplicate_seed_flag)
                VALUES (%s, %s, %s, %s, 0)
                RETURNING id
                """,
                (entry.seed, entry.x, entry.z, entry.claimed_size),
            )
            conn.commit()

        return {"status": "success", "message": "Data processed successfully"}

    finally:
        cur.close()
        conn.close()