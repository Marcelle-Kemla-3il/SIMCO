from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class FacialFeatures(BaseModel):
    emotions: Dict[str, float]  # {"happy": 0.8, "sad": 0.1, ...}
    facial_expressions: Dict[str, float]  # {"smile": 0.9, "frown": 0.1, ...}
    eye_contact: float = Field(..., ge=0.0, le=1.0)
    attention_level: float = Field(..., ge=0.0, le=1.0)

class FacialAnalysisRequest(BaseModel):
    answer_id: int
    video_path: Optional[str] = None
    image_frames: Optional[List[str]] = None  # Base64 encoded frames

class FacialAnalysisResponse(BaseModel):
    id: int
    observed_confidence: float
    confidence_discrepancy: float
    emotions: Dict[str, float]
    attention_level: float
    analysis_summary: str

class CognitiveProfileAnalysis(BaseModel):
    actual_performance: float = Field(..., ge=0.0, le=1.0)
    declared_confidence: float = Field(..., ge=0.0, le=1.0)
    observed_confidence: float = Field(..., ge=0.0, le=1.0)
    dunning_kruger_score: Optional[float] = Field(None, ge=-1.0, le=1.0)
    impostor_syndrome_score: Optional[float] = Field(None, ge=-1.0, le=1.0)
    metacognitive_accuracy: Optional[float] = Field(None, ge=0.0, le=1.0)

class CognitiveProfileResponse(BaseModel):
    id: int
    session_id: int
    cognitive_profile_type: str  # "confident", "dunning-kruger", "impostor", "accurate"
    risk_level: str  # "low", "medium", "high"
    cognitive_curve_position: Dict[str, float]  # {"x": confidence, "y": performance}
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    detailed_analysis: Dict[str, Any]

class ReportRequest(BaseModel):
    session_id: int
    report_type: str = Field(default="comprehensive", pattern="^(summary|comprehensive)$")
    format: str = Field(default="html", pattern="^(html|pdf)$")

class ReportResponse(BaseModel):
    id: int
    session_id: int
    summary: str
    html_content: Optional[str] = None
    pdf_path: Optional[str] = None
    charts_data: Optional[Dict[str, Any]] = None
    generated_at: datetime
