import os
import jwt
import httpx
import time
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv
from shared.logger_client import send_log
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

SECRET = os.getenv("JWT_SECRET")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # allow frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- SERVICE URLS ----------------

AUTH_URL = "http://localhost:8001"
ENROLL_URL = "http://localhost:8002"
DETECT_URL = "http://localhost:8003"
RECOGNITION_URL = "http://localhost:8004"
ATTENDANCE_URL = "http://localhost:8005"

security = HTTPBearer()


# ---------------- MODELS ----------------

class LoginRequest(BaseModel):
    username: str
    password: str


class AttendanceRequest(BaseModel):
    employee_id: int
    confidence: float


# ---------------- REQUEST LOGGING MIDDLEWARE ----------------

@app.middleware("http")
async def log_requests(request: Request, call_next):

    start_time = time.time()

    response = await call_next(request)

    process_time = round(time.time() - start_time, 4)

    await send_log(
        "gateway-service",
        "INFO",
        f"{request.method} {request.url.path} completed in {process_time}s"
    )

    return response


# ---------------- TOKEN VERIFICATION ----------------

def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])

        return payload

    except jwt.ExpiredSignatureError:

        raise HTTPException(status_code=401, detail="Token expired")

    except jwt.InvalidTokenError:

        raise HTTPException(status_code=401, detail="Invalid token")


# ---------------- ADMIN CHECK ----------------

def admin_only(user=Depends(verify_token)):

    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    return user


# ---------------- LOGIN ----------------

@app.post("/api/login")
async def login(payload: LoginRequest):

    async with httpx.AsyncClient(timeout=10) as client:

        response = await client.post(
            f"{AUTH_URL}/login",
            json=payload.dict()
        )

    await send_log("gateway-service", "INFO", "Login forwarded to auth service")

    if response.status_code != 200:
        await send_log("gateway-service", "ERROR", "Login failed")

        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    return response.json()


# ---------------- ENROLL EMPLOYEE ----------------

@app.post("/api/enroll")
async def enroll_employee(
    name: str = Form(...),
    employee_code: str = Form(...),
    image: UploadFile = File(...),
    user=Depends(admin_only)
):

    async with httpx.AsyncClient(timeout=20) as client:

        response = await client.post(
            f"{ENROLL_URL}/enroll",
            data={
                "name": name,
                "employee_code": employee_code
            },
            files={
                "image": (image.filename, image.file, image.content_type)
            }
        )

    await send_log("gateway-service", "INFO", "Enrollment request forwarded")

    if response.status_code != 200:

        await send_log("gateway-service", "ERROR", "Enrollment failed")

        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    return response.json()


# ---------------- FACE DETECTION ----------------

@app.post("/api/detect")
async def detect_faces(
    image: UploadFile = File(...),
    user=Depends(verify_token)
):

    async with httpx.AsyncClient(timeout=80) as client:

        response = await client.post(
            f"{DETECT_URL}/detect",
            files={
                "file": (image.filename, image.file, image.content_type)
            }
        )

    await send_log("gateway-service", "INFO", "Detection service called")

    if response.status_code != 200:

        await send_log("gateway-service", "ERROR", "Detection failed")

        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    return response.json()


# ---------------- FACE RECOGNITION ----------------

@app.post("/api/recognize")
async def recognize_face(
    image: UploadFile = File(...),
    user=Depends(verify_token)
):

    async with httpx.AsyncClient(timeout=60) as client:

        response = await client.post(
            f"{RECOGNITION_URL}/recognize",
            files={
                "file": (image.filename, image.file, image.content_type)
            }
        )

    await send_log("gateway-service", "INFO", "Recognition service called")

    if response.status_code != 200:

        await send_log("gateway-service", "ERROR", "Recognition failed")

        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    recognition_result = response.json()

    if not recognition_result.get("recognized"):
        return recognition_result

    async with httpx.AsyncClient(timeout=10) as client:
        attendance_response = await client.post(
            f"{ATTENDANCE_URL}/mark",
            json={
                "employee_id": recognition_result["employee_id"],
                "confidence": recognition_result["confidence"]
            }
        )

    if attendance_response.status_code != 200:
        await send_log("gateway-service", "ERROR", "Auto attendance failed")

        raise HTTPException(
            status_code=attendance_response.status_code,
            detail=attendance_response.text
        )

    recognition_result["attendance"] = attendance_response.json()

    await send_log("gateway-service", "INFO", "Attendance marked after recognition")

    return recognition_result


# ---------------- MARK ATTENDANCE ----------------

@app.post("/api/attendance")
async def mark_attendance(
    payload: AttendanceRequest,
    user=Depends(verify_token)
):

    async with httpx.AsyncClient(timeout=10) as client:

        response = await client.post(
            f"{ATTENDANCE_URL}/mark",
            json=payload.dict()
        )

    await send_log("gateway-service", "INFO", "Attendance request forwarded")

    if response.status_code != 200:

        await send_log("gateway-service", "ERROR", "Attendance failed")

        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    return response.json()


# ---------------- TEST ROUTE ----------------

@app.get("/api/protected")
async def protected_route(user=Depends(verify_token)):

    await send_log(
        "gateway-service",
        "INFO",
        f"Protected route accessed by {user.get('username')}"
    )

    return {
        "message": "Access granted",
        "user": user
    }
