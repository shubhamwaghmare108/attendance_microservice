start cmd /k "venv\Scripts\activate && uvicorn logging_service.main:app --port 9000 --reload"

start cmd /k "venv\Scripts\activate && uvicorn auth_service.main:app --port 8001 --reload"

start cmd /k "venv\Scripts\activate && uvicorn enrollment_service.main:app --port 8002 --reload"

start cmd /k "venv\Scripts\activate && uvicorn face_detection_service.main:app --port 8003 --reload"

start cmd /k "venv\Scripts\activate && uvicorn face_recognition_service.main:app --port 8004 --reload"

start cmd /k "venv\Scripts\activate && uvicorn attendance_service.main:app --port 8005 --reload"

start cmd /k "venv\Scripts\activate && uvicorn gateway_service.main:app --port 8000 --reload"