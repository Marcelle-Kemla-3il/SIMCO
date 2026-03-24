from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.ml import predict_true_confidence

router = APIRouter()


class TrueConfidenceRequest(BaseModel):
    self_confidence: float = Field(..., ge=0.0, le=1.0)
    face_confidence_per_question: List[float] = Field(default_factory=list)


class TrueConfidenceResponse(BaseModel):
    true_confidence_normalized: float
    true_confidence: float
    input_summary: dict
    model: str


@router.get("/health")
def health_check() -> dict:
    return {"status": "ok", "service": "SIMCO Logic"}


@router.get("/")
def root() -> dict:
    return {"message": "Welcome to SIMCO Logic API"}


@router.post("/analyze/true-confidence", response_model=TrueConfidenceResponse)
def analyze_true_confidence(payload: TrueConfidenceRequest):
    if payload.self_confidence is None:
        raise HTTPException(status_code=400, detail="self_confidence is required")

    try:
        for value in payload.face_confidence_per_question:
            if value < 0.0 or value > 1.0:
                raise HTTPException(
                    status_code=422,
                    detail="face_confidence_per_question values must be normalized in [0,1]",
                )

        return predict_true_confidence(
            self_confidence=payload.self_confidence,
            face_confidence_per_question=payload.face_confidence_per_question,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"True confidence inference failed: {exc}") from exc
