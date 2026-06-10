from face_detection_service.core.yolo_detector import YOLOFaceDetector


class DetectionService:

    def __init__(self):

        self.detector = YOLOFaceDetector()

    def detect_faces(self, frame):

        return self.detector.detect(frame)