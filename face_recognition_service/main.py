from fastapi import FastAPI
from face_recognition_service.api.routes import router

app = FastAPI()

app.include_router(router)