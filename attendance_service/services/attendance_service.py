from attendance_service.db.attendance_repository import (
    employee_exists,
    get_last_attendance,
    insert_attendance
)


class AttendanceService:

    def mark_attendance(self, employee_id, confidence):

        if not employee_exists(employee_id):
            return {
                "error": "Employee not found",
                "status_code": 404
            }

        last = get_last_attendance(employee_id)

        if last is None:
            attendance_type = "checkin"

        elif last["type"] == "checkin":
            attendance_type = "checkout"

        else:
            attendance_type = "checkin"

        insert_attendance(employee_id, attendance_type, confidence)

        return {
            "employee_id": employee_id,
            "type": attendance_type
        }
