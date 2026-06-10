from fastapi import APIRouter, UploadFile, File, HTTPException
import numpy as np
import cv2

from face_detection_service.services.detection_service import DetectionService

router = APIRouter()

service = DetectionService()


@router.post("/detect")
async def detect_faces(file: UploadFile = File(...)):

    image = await file.read()

    nparr = np.frombuffer(image, np.uint8)

    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid image")

    faces = service.detect_faces(frame)

    return {"faces": faces}
