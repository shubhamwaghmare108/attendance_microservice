import os
import cv2
import numpy as np
import aiomysql
import httpx

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from dotenv import load_dotenv
from shared.logger_client import send_log

load_dotenv()

app = FastAPI()

DETECTION_SERVICE_URL = "http://localhost:8003/detect"
EMBEDDING_SERVICE_URL = "http://localhost:8004/embed"


# ---------------- DATABASE CONNECTION ----------------
async def get_connection():
    return await aiomysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        db=os.getenv("DB_NAME"),
        autocommit=False
    )


# ---------------- CALL FACE DETECTION SERVICE ----------------
async def detect_face(image_bytes):

    files = {
        "file": ("image.jpg", image_bytes, "image/jpeg")
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            DETECTION_SERVICE_URL,
            files=files
        )

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Face detection failed")

    return response.json()


# ---------------- CALL EMBEDDING SERVICE ----------------
async def get_embedding(face_bytes):

    files = {
        "file": ("face.jpg", face_bytes, "image/jpeg")
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            EMBEDDING_SERVICE_URL,
            files=files
        )

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Embedding service failed")

    return response.json()["embedding"]


# ---------------- ENROLL EMPLOYEE ----------------
@app.post("/enroll")
async def enroll_employee(
    name: str = Form(...),
    employee_code: str = Form(...),
    image: UploadFile = File(...)
):

    image_bytes = await image.read()

    # --------- FACE DETECTION ---------
    detection_result = await detect_face(image_bytes)

    faces = detection_result.get("faces", [])

    if len(faces) == 0:
        raise HTTPException(status_code=400, detail="No face detected")

    if len(faces) > 1:
        faces = sorted(
            faces,
            key=lambda item: int(item["w"]) * int(item["h"]),
            reverse=True
        )

        largest_area = int(faces[0]["w"]) * int(faces[0]["h"])
        second_area = int(faces[1]["w"]) * int(faces[1]["h"])

        if second_area > largest_area * 0.45:
            raise HTTPException(status_code=400, detail="Multiple faces detected")

    face = faces[0]

    # Convert detection format (x,y,w,h) to (x1,y1,x2,y2)
    x = int(face["x"])
    y = int(face["y"])
    w = int(face["w"])
    h = int(face["h"])

    x1 = x
    y1 = y
    x2 = x + w
    y2 = y + h

    # --------- DECODE IMAGE ---------
    np_img = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image")

    img_h, img_w, _ = img.shape

    # Safety clipping
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(img_w, x2)
    y2 = min(img_h, y2)

    # --------- CROP FACE ---------
    face_crop = img[y1:y2, x1:x2]

    if face_crop.size == 0:
        raise HTTPException(status_code=400, detail="Face crop failed")

    # Encode cropped face
    success, buffer = cv2.imencode(".jpg", face_crop)

    if not success:
        raise HTTPException(status_code=500, detail="Face encoding failed")

    face_bytes = buffer.tobytes()

    # --------- GET EMBEDDING ---------
    embedding = await get_embedding(face_bytes)

    embedding_vector = np.array(embedding, dtype=np.float32)

    # --------- STORE IN DATABASE ---------
    conn = await get_connection()

    try:
        async with conn.cursor(aiomysql.DictCursor) as cursor:

            await cursor.execute(
                "SELECT employee_id FROM employees WHERE employee_code=%s",
                (employee_code,)
            )

            existing = await cursor.fetchone()

            if existing:
                raise HTTPException(status_code=400, detail="Employee already exists")

            await cursor.execute(
                """
                INSERT INTO employees (name, employee_code)
                VALUES (%s, %s)
                """,
                (name, employee_code)
            )

            employee_id = cursor.lastrowid

            await cursor.execute(
                """
                INSERT INTO face_embeddings (employee_id, embedding)
                VALUES (%s, %s)
                """,
                (
                    employee_id,
                    embedding_vector.tobytes()
                )
            )
        await conn.commit()
    except Exception:
        await conn.rollback()
        raise
    finally:
        conn.close()

    # --------- LOGGING ---------
    await send_log(
        "enrollment-service",
        "INFO",
        f"Employee enrolled: {employee_code}"
    )

    return {
        "message": "Employee enrolled successfully",
        "employee_id": employee_id,
        "employee_code": employee_code
    }
