from fastapi import APIRouter, UploadFile, File, HTTPException
import numpy as np
import cv2

from face_recognition_service.services.recognition_service import RecognitionService

router = APIRouter()

service = RecognitionService()
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)


def decode_image(image_bytes):
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid image")

    return frame


def crop_largest_face(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(60, 60)
    )

    if len(faces) == 0:
        raise HTTPException(status_code=400, detail="No face detected")

    x, y, w, h = max(faces, key=lambda box: box[2] * box[3])
    return frame[y:y + h, x:x + w]


@router.post("/embed")
async def embed(file: UploadFile = File(...)):
    image_bytes = await file.read()
    frame = decode_image(image_bytes)
    embedding = service.embed(frame)

    return {"embedding": embedding.tolist()}


@router.post("/recognize")
async def recognize(file: UploadFile = File(...)):
    image_bytes = await file.read()
    frame = decode_image(image_bytes)
    face = crop_largest_face(frame)
    result = service.recognize(face)

    return result
