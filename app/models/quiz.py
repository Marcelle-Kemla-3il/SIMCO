from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Quiz(Base):
    __tablename__ = "quizzes"
    
    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String(100), nullable=False)
    level = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    questions = Column(JSON, nullable=False)  # List of questions with choices
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    sessions = relationship("QuizSession", back_populates="quiz")

class QuizSession(Base):
    __tablename__ = "quiz_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    student_id = Column(String(100), nullable=False)  # Simple identifier
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    quiz = relationship("Quiz", back_populates="sessions")
    answers = relationship("Answer", back_populates="session")
    cognitive_profile = relationship("CognitiveProfile", back_populates="session", uselist=False)

class Answer(Base):
    __tablename__ = "answers"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("quiz_sessions.id"), nullable=False)
    question_index = Column(Integer, nullable=False)
    selected_answer = Column(String(500), nullable=False)
    confidence_level = Column(Float, nullable=False)  # 0-1 scale
    response_time_ms = Column(Integer, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    
    # Relationships
    session = relationship("QuizSession", back_populates="answers")
    facial_analysis = relationship("FacialAnalysis", back_populates="answer", uselist=False)
