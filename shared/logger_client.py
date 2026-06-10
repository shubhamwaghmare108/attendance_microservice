import httpx
from datetime import datetime, timezone

LOGGING_URL = "http://localhost:9000/log"


async def send_log(service_name, level, message):

    payload = {
        "service_name": service_name,
        "level": level,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    async with httpx.AsyncClient() as client:
        try:
            await client.post(LOGGING_URL, json=payload)
        except:
            pass