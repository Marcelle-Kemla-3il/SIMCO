from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Question(BaseModel):
    question: str
    choices: List[str]
    correct_answer: str
    explanation: Optional[str] = None

class QuizGenerate(BaseModel):
    subject: str = Field(..., description="Matière du quiz")
    level: str = Field(..., description="Niveau: débutant, intermédiaire, avancé")
    sector: Optional[str] = Field(default=None, description="Secteur professionnel (ex: informatique, finance, santé)")
    difficulty: Optional[str] = Field(default=None, description="Difficulté (easy/medium/hard) ou équivalent")
    num_questions: int = Field(default=10, ge=1, description="Nombre de questions souhaité")
    topics: Optional[List[str]] = Field(default=None, description="Sujets spécifiques à couvrir")
    country: Optional[str] = Field(default=None, description="Pays/région pour contextualiser le contenu")
    force_refresh: Optional[bool] = Field(default=False, description="Ignorer le cache et forcer un nouveau quiz")
    class_level: Optional[str] = Field(default=None, description="Classe/année/niveau précis")

class QuizResponse(BaseModel):
    id: int
    subject: str
    level: str
    title: str
    questions: List[Question]
    created_at: datetime

class AnswerSubmit(BaseModel):
    session_id: int
    question_index: int
    selected_answer: str
    confidence_level: float = Field(..., ge=0.0, le=1.0, description="Niveau de confiance déclaré (0-1)")
    response_time_ms: int

class AnswerResponse(BaseModel):
    id: int
    is_correct: bool
    correct_answer: str
    explanation: Optional[str] = None
    confidence_analysis: Optional[Dict[str, Any]] = None

class QuizSessionCreate(BaseModel):
    quiz_id: int
    student_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    subject: Optional[str] = None
    level: Optional[str] = None
    class_level: Optional[str] = None

class QuizSessionResponse(BaseModel):
    id: int
    quiz_id: int
    student_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_questions: int
    answered_questions: int
    score: Optional[float] = None
