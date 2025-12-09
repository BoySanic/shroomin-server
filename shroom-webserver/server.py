from fastapi import FastAPI, HTTPException, Request
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import List
from datetime import datetime, timezone
from Crypto.Hash import SHA256
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS
import psycopg2
import psycopg2.extras
import os
import secrets, string, base64, json, hashlib
import logging

pwd = os.getenv("SHROOM_KEY_PW")

def import_key():
    with open("shroom.priv", "rb") as f:
        key_text = f.read()
        return ECC.import_key(key_text, pwd, 'p256')

def generate_key_pair():
    mykey = ECC.generate(curve='p256')
    pub_out = mykey.public_key().export_key(format='PEM')
    priv_out = mykey.export_key(format='PEM',
                                passphrase=pwd,
                                protection='PBKDF2WithHMAC-SHA512AndAES256-CBC',
                                prot_params={'iteration_count':131072})
    with open("shroom.priv", "wb") as f:
        f.write(priv_out.encode('utf-8'))
    with open("shroom.pub", "wb") as f:
        f.write(pub_out.encode('utf-8'))
    return mykey

def get_jwt_headers():
    headers = {
        "alg": "ECC256",
        "typ": "JWT"
    }
    return headers

def encode_headers(header):
    header_bytes = json.dumps(header).encode("utf-8")
    return base64.urlsafe_b64encode(header_bytes).decode("utf-8")

def encode_payload(payload):
    payload_bytes = json.dumps(payload).encode("utf-8")
    return base64.urlsafe_b64encode(payload_bytes).decode("utf-8")

def assemble_jwt(enc_header, enc_payload, priv_key):
    message = (enc_header + "." + enc_payload).encode("utf-8")

    hash = SHA256.new(message)
    signer = DSS.new(priv_key, 'deterministic-rfc6979')
    signature = signer.sign(hash)
    encoded_signature = base64.urlsafe_b64encode(signature).decode("utf-8")
    return (enc_header + "." + enc_payload + "." + encoded_signature)

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
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application starting up (lifespan)...")
    await load_or_generate_key()
    yield
    print("Application shuting down (lifespan)...")

# FastAPI App
app = FastAPI(lifespan=lifespan)
logger = logging.getLogger("server")

# Pydantic Models

class UserEntry(BaseModel):
    discord_id: int

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

async def load_or_generate_key():
    logger.info("Initializing ECC key… (PID %s)", os.getpid())
    if not os.path.exists("shroom.priv"):
        key = generate_key_pair()
    else:
        key = import_key()
    pem = key.export_key(
        format="PEM",
        passphrase=pwd,
        protection="PBKDF2WithHMAC-SHA512AndAES256-CBC",
        prot_params={"iteration_count": 131072},
    )
    logger.info("ECC key ready with curve: %s", key.curve)
    app.state.key = key
# API Endpoint

async def authenticate(api_key: string):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    encoded_header, encoded_payload, encoded_signature = api_key.split(".")
    discord_id, created_at = base64.urlsafe_b64decode(encoded_payload).decode("utf-8").removeprefix('"').removesuffix('"').split(".", 1)

    padding_correction = "=" * ((4 - len(encoded_signature) % 4) % 4)
    received_signature = base64.urlsafe_b64decode(encoded_signature + padding_correction)
    received_message = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    cur.execute(
        f"""
        SELECT id FROM users
        WHERE discord_id = %s
        """, (discord_id,)
    )
    user_id = cur.fetchone()
    if user_id:
        print(app.state.key.public_key().export_key(format="PEM"))
        hash = SHA256.new(received_message)
        verifier = DSS.new(app.state.key.public_key(), 'deterministic-rfc6979')
        try:
            verifier.verify(hash, received_signature)
        except:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid API Key provided",
            )
    return int(user_id[0])

@app.get("/sb_leaderboard")
async def small_biomes_lb(request: Request):
    return await get_lb(True)

@app.get("/lb_leaderboard")
async def large_biomes_lb(request: Request):
    return await get_lb(False)

async def get_lb(small_biomes: bool):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    table_name = "small_biomes" if small_biomes else "large_biomes"

    cur.execute(
        f"""
            SELECT u.discord_id, seed, claimed_size, calculated_size, id from {table_name} mush
            JOIN users u on u.id = mush.user_id
            ORDER BY mush.claimed_size
            GROUP BY u.discord_id
            LIMIT 10
        """)
    message = {}
    results = cur.fetchall()
    place = 1
    for result in results:
        message[place] = {
            "discord_id": result[0],
            "seed": result[1],
            "claimed_size": result[2],
            "calculated_size": result[3],
            "result_id": result[4]
        }
        place += 1
    return message

@app.post("/register")
async def receive_register(payload: UserEntry, request: Request):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if "api-key" not in request.headers:    
        raise HTTPException(
            status_code=400,
            detail=f"API Key not provided",
        )
    if await authenticate(request.headers['api-key']) == 13:
        cur.execute(
            f"""
            SELECT id FROM users
            WHERE discord_id = %s
            """, (payload.discord_id,)
        )
        user_id = cur.fetchone()
        if not user_id:
            try:
                print(app.state.key.public_key().export_key(format="PEM"))
                encoded_header = encode_headers(get_jwt_headers())
                created_at = datetime.now(tz=timezone.utc)
                payload_rebuilt = f"{payload.discord_id}.{created_at.timestamp()}"
                encoded_payload = encode_payload(payload_rebuilt)
                full_token = assemble_jwt(encoded_header, encoded_payload, app.state.key)

                print(f"Inserting id {payload.discord_id} and created_at {created_at}")
                cur.execute(
                    f"""
                    INSERT INTO users (discord_id, created_at) values
                    (%s, %s)
                    """, (payload.discord_id, created_at)
                )
                conn.commit()
                return full_token
            except Exception as e:
                print(f"Encountered an error: {e}")

            finally:
                cur.close()
                conn.close()
        else:
            raise HTTPException(
                status_code=400,
                detail=f"User already exists",
            )
    else:
        raise HTTPException(
                status_code=401,
                detail=f"Unauthorized",
            )

@app.post("/small_biomes")
async def small_biomes(payload: Payload, request: Request):
    return await receive_payload(payload, request, True)

@app.post("/large_biomes")
async def large_biomes(payload: Payload, request: Request):
    return await receive_payload(payload, request, False)

async def receive_payload(payload: Payload, request: Request, small_biomes: bool):
    if(small_biomes):
        TABLE_NAME = os.getenv("SHROOM_SB_TABLE_NAME")
    else:
        TABLE_NAME = os.getenv("SHROOM_LB_TABLE_NAME")
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if "api-key" not in request.headers:
        raise HTTPException(
            status_code=400,
            detail=f"API Key not provided",
        )
    api_key = request.headers['api-key']
    user_id = await authenticate(api_key)
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
                # Exact match found -> reject
                continue

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
                    INSERT INTO {TABLE_NAME} (seed, x, z, claimed_size, duplicate_seed_flag, user_id)
                    VALUES (%s, %s, %s, %s, 0, %s)
                    RETURNING id
                    """,
                    (entry.seed, entry.x, entry.z, entry.claimed_size, user_id),
                )
                conn.commit()
                continue

            # 3. No match at all → insert normally with flag = 0
            cur.execute(
                f"""
                INSERT INTO {TABLE_NAME} (seed, x, z, claimed_size, duplicate_seed_flag, user_id)
                VALUES (%s, %s, %s, %s, 0, %s)
                RETURNING id
                """,
                (entry.seed, entry.x, entry.z, entry.claimed_size, user_id),
            )
            conn.commit()

        return {"status": "success", "message": "Data processed successfully"}

    finally:
        cur.close()
        conn.close()