import os
from datetime import datetime, timedelta, timezone

import jwt
import bcrypt
import aiomysql
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from shared.logger_client import send_log


# ---------------- LOAD ENV ----------------
load_dotenv()

SECRET = os.getenv("JWT_SECRET")

app = FastAPI()


# ---------------- MODELS ----------------
class RegisterModel(BaseModel):
    username: str
    password: str


class LoginModel(BaseModel):
    username: str
    password: str


# ---------------- DB CONNECTION ----------------
async def get_connection():
    return await aiomysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        db=os.getenv("DB_NAME"),
        autocommit=True
    )


# ---------------- REGISTER ----------------
@app.post("/register")
async def register(data: RegisterModel):

    conn = await get_connection()

    async with conn.cursor(aiomysql.DictCursor) as cursor:

        # Hash password
        hashed_password = bcrypt.hashpw(
            data.password.encode(),
            bcrypt.gensalt()
        ).decode()

        try:
            await cursor.execute(
                """
                INSERT INTO users (username, password_hash, role)
                VALUES (%s, %s, %s)
                """,
                (data.username, hashed_password, "user")
            )
        except Exception:
            raise HTTPException(status_code=400, detail="User already exists")

    conn.close()

    await send_log("auth-service", "INFO", f"User registered: {data.username}")

    return {"message": "User registered successfully"}


# ---------------- LOGIN ----------------
@app.post("/login")
async def login(data: LoginModel):

    conn = await get_connection()

    async with conn.cursor(aiomysql.DictCursor) as cursor:

        await cursor.execute(
            "SELECT * FROM users WHERE username=%s",
            (data.username,)
        )

        user = await cursor.fetchone()

        if not user:
            await send_log("auth-service", "WARNING", "Invalid username")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        elif not bcrypt.checkpw(
            data.password.encode(),
            user["password_hash"].encode()
        ):
            await send_log("auth-service", "WARNING", "Wrong password")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Create JWT with role
        token = jwt.encode(
            {
                "user_id": user["id"],
                "role": user["role"],   #  Important for Gateway authorization
                "exp": datetime.now(timezone.utc) + timedelta(hours=2)
            },
            SECRET,
            algorithm="HS256"
        )

    conn.close()

    await send_log("auth-service", "INFO", f"User logged in: {data.username}")

    return {"token": token}