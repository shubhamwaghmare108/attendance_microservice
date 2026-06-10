from fastapi import FastAPI
from attendance_service.api.routes import router

app = FastAPI()

app.include_router(router)