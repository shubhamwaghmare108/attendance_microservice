from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from attendance_service.services.attendance_service import AttendanceService

router = APIRouter()

service = AttendanceService()


class AttendanceRequest(BaseModel):
    employee_id: int
    confidence: float


@router.post("/mark")
def mark_attendance(data: AttendanceRequest):

    result = service.mark_attendance(
        data.employee_id,
        data.confidence
    )

    if "error" in result:
        raise HTTPException(
            status_code=result["status_code"],
            detail=result["error"]
        )

    return result
