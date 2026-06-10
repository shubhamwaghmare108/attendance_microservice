import os
import numpy as np
import aiomysql
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from shared.logger_client import send_log
from dotenv import load_dotenv
import httpx
load_dotenv()

app = FastAPI()

# ---------------- DB CONNECTION ----------------
async def get_connection():
    return await aiomysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        db=os.getenv("DB_NAME"),
        autocommit=True
    )


# ---------------- DUMMY EMBEDDING ----------------
def generate_embedding():
    # For now generate random 128-d vector
    return np.random.rand(128).astype(np.float32)


# ---------------- ENROLL ENDPOINT ----------------
@app.post("/enroll")
async def enroll_employee(
    name: str = Form(...),
    employee_code: str = Form(...),
    image: UploadFile = File(...)
):

    # Generate embedding (later replace with real face model)
    embedding = generate_embedding()

    conn = await get_connection()

    async with conn.cursor(aiomysql.DictCursor) as cursor:

        # Check duplicate employee_code
        await cursor.execute(
            "SELECT id FROM employees WHERE employee_code=%s",
            (employee_code,)
        )
        existing = await cursor.fetchone()

        if existing:
            raise HTTPException(status_code=400, detail="Employee already exists")
        
        # Insert employee
        await cursor.execute(
            """
            INSERT INTO employees (name, employee_code, embedding)
            VALUES (%s, %s, %s)
            """,
            (name, employee_code, embedding.tobytes())
        )

    conn.close()

    await send_log(
        "enrollment-service",
        "INFO",
        f"Employee enrolled: {employee_code}"
    )

    return {
        "message": "Employee enrolled successfully",
        "employee_code": employee_code
    }