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
    user_name = Column(String(200), nullable=True)  # Nom de l'utilisateur
    user_email = Column(String(320), nullable=True, index=True)  # Email de l'utilisateur
    subject = Column(String(100), nullable=True)  # Matière
    level = Column(String(50), nullable=True)  # Niveau
    class_level = Column(String(50), nullable=True)  # Classe/année/niveau précis
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    quiz = relationship("Quiz", back_populates="sessions")
    answers = relationship("Answer", back_populates="session")
    emotion_events = relationship("EmotionEvent", back_populates="session")

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


class EmotionEvent(Base):
    __tablename__ = "emotion_events"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("quiz_sessions.id"), nullable=False, index=True)
    question_index = Column(Integer, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    faces_count = Column(Integer, nullable=True)
    dominant_emotion = Column(String(50), nullable=True)
    emotions = Column(JSON, nullable=True)
    confidence_score = Column(Float, nullable=True)

    session = relationship("QuizSession", back_populates="emotion_events")
