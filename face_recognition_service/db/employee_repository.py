import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        db=os.getenv("DB_NAME"),
        autocommit=True
    )


def get_all_embeddings():

    conn = get_connection()

    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute("""
        SELECT
            e.employee_id,
            e.employee_code,
            e.name,
            fe.embedding
        FROM face_embeddings fe
        INNER JOIN employees e ON e.employee_id = fe.employee_id
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows
