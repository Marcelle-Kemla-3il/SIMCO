from app.core.database import engine, Base
from app.models.quiz import Quiz, QuizSession, Answer
from app.models.cognitive import FacialAnalysis, CognitiveProfile, Report

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    create_tables()
    print("Database tables created successfully!")
