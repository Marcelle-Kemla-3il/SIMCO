from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional


class QuizResultPayload(BaseModel):
    score: int = Field(..., ge=0)
    total_questions: int = Field(..., gt=0)
    percentage: float = Field(..., ge=0, le=100)
    level: Optional[str] = None
    message: Optional[str] = None
    recommendations: List[str] = Field(default_factory=list)
    self_confidence: Optional[float] = None
    true_confidence: Optional[float] = None
    profile_label: Optional[str] = None


class QuestionResultPayload(BaseModel):
    question: str
    is_correct: Optional[bool] = None
    confidence_analysis: Optional[str] = None
    face_confidence: Optional[float] = None


class DunningKrugerPayload(BaseModel):
    actual_score: Optional[float] = None
    declared_confidence: Optional[float] = None
    calibration_score: Optional[float] = None


class NotificationRequest(BaseModel):
    user_name: str = Field(..., min_length=1)
    user_email: EmailStr
    quiz_result: QuizResultPayload
    question_results: List[QuestionResultPayload] = Field(default_factory=list)
    dunning_kruger: Optional[DunningKrugerPayload] = None


class NotificationResponse(BaseModel):
    success: bool
    detail: str
