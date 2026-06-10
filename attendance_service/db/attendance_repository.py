from datetime import datetime
from attendance_service.db.connection import get_connection


def employee_exists(employee_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT employee_id
        FROM employees
        WHERE employee_id=%s
        """,
        (employee_id,)
    )

    result = cursor.fetchone()
    conn.close()

    return result is not None


def get_last_attendance(employee_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT type 
        FROM attendance
        WHERE employee_id=%s
        ORDER BY check_time DESC
        LIMIT 1
        """,
        (employee_id,)
    )

    result = cursor.fetchone()
    conn.close()

    return result


def insert_attendance(employee_id, attendance_type, confidence):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO attendance(employee_id, check_time, type, confidence)
        VALUES(%s,%s,%s,%s)
        """,
        (employee_id, datetime.now(), attendance_type, confidence)
    )

    conn.commit()
    conn.close()
