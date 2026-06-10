import numpy as np
from face_recognition_service.core.facenet_encoder import FaceNetEncoder
from face_recognition_service.db.employee_repository import get_all_embeddings


class RecognitionService:

    def __init__(self):
        self.encoder = FaceNetEncoder()
        self.match_threshold = 1.35

    def embed(self, face_image):
        return self.encoder.encode(face_image)

    def recognize(self, face_image):
        query_embedding = self.embed(face_image)
        employees = get_all_embeddings()

        best_match = None
        best_distance = 999

        for emp in employees:

            db_embedding = np.frombuffer(emp["embedding"], dtype=np.float32)

            distance = np.linalg.norm(query_embedding - db_embedding)

            if distance < best_distance:
                best_distance = distance
                best_match = emp

        if best_distance < self.match_threshold:
            return {
                "recognized": True,
                "employee_id": best_match["employee_id"],
                "employee_code": best_match["employee_code"],
                "name": best_match["name"],
                "confidence": float(1 / (1 + best_distance)),
                "distance": float(best_distance)
            }

        return {
            "recognized": False,
            "employee_id": None,
            "employee_code": None,
            "name": None,
            "confidence": 0.0,
            "distance": float(best_distance) if employees else None
        }
