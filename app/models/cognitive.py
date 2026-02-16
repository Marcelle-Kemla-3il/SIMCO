from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class FacialAnalysis(Base):
    __tablename__ = "facial_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    answer_id = Column(Integer, ForeignKey("answers.id"), nullable=False)
    
    # Facial features
    emotions = Column(JSON, nullable=True)  # {"happy": 0.8, "sad": 0.1, ...}
    facial_expressions = Column(JSON, nullable=True)  # {"smile": 0.9, "frown": 0.1, ...}
    eye_contact = Column(Float, nullable=True)  # 0-1 scale
    attention_level = Column(Float, nullable=True)  # 0-1 scale
    
    # Confidence indicators
    observed_confidence = Column(Float, nullable=True)  # ML-predicted confidence
    confidence_discrepancy = Column(Float, nullable=True)  # declared vs observed
    
    # Metadata
    analysis_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    video_path = Column(String(500), nullable=True)
    
    # Relationships
    answer = relationship("Answer", back_populates="facial_analysis")

class CognitiveProfile(Base):
    __tablename__ = "cognitive_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("quiz_sessions.id"), nullable=False)
    
    # Performance metrics
    actual_performance = Column(Float, nullable=False)  # 0-1 scale
    declared_confidence = Column(Float, nullable=False)  # Average declared confidence
    observed_confidence = Column(Float, nullable=False)  # Average observed confidence
    
    # Cognitive biases
    dunning_kruger_score = Column(Float, nullable=True)  # Overconfidence indicator
    impostor_syndrome_score = Column(Float, nullable=True)  # Underconfidence indicator
    metacognitive_accuracy = Column(Float, nullable=True)  # Self-awareness accuracy
    
    # Classification
    cognitive_profile_type = Column(String(50), nullable=False)  # "confident", "dunning-kruger", "impostor", "accurate"
    risk_level = Column(String(20), nullable=False)  # "low", "medium", "high"
    
    # Recommendations
    strengths = Column(JSON, nullable=True)  # List of mastered topics
    weaknesses = Column(JSON, nullable=True)  # List of topics to improve
    recommendations = Column(JSON, nullable=True)  # Personalized recommendations
    
    # Position on cognitive curve
    cognitive_curve_position = Column(JSON, nullable=True)  # {"x": confidence, "y": performance}
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("QuizSession", back_populates="cognitive_profile")

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("quiz_sessions.id"), nullable=False)
    
    # Report content
    html_content = Column(Text, nullable=True)
    pdf_path = Column(String(500), nullable=True)
    summary = Column(Text, nullable=False)
    
    # Visualizations
    charts_data = Column(JSON, nullable=True)  # Plotly charts data
    
    # Metadata
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    report_type = Column(String(50), default="comprehensive")  # "summary", "comprehensive"
