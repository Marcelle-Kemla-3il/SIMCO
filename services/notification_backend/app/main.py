from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .settings import settings
from .schemas import NotificationRequest, NotificationResponse
from .email_service import send_notification_email


app = FastAPI(
    title="SIMCO Notification Service",
    version="1.0.0",
    description="Dedicated service to send quiz result notifications by email.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "notification_backend",
        "smtp_host": settings.MAIL_HOST,
        "smtp_port": settings.MAIL_PORT,
    }


@app.post("/notifications/quiz-result", response_model=NotificationResponse)
def send_quiz_result_notification(payload: NotificationRequest):
    success, detail = send_notification_email(payload)
    if not success:
        raise HTTPException(status_code=500, detail=detail)
    return NotificationResponse(success=True, detail=detail)
