from app.core.database import engine, Base
from app.models.quiz import Quiz, QuizSession, Answer, EmotionEvent
try:
    from app.models.cognitive import FacialAnalysis, CognitiveProfile, Report
except Exception:
    FacialAnalysis = None
    CognitiveProfile = None
    Report = None

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

    # Best-effort lightweight migrations for SQLite dev DBs.
    # This keeps older local DB files compatible without requiring Alembic.
    try:
        if engine.dialect.name != "sqlite":
            return

        def _has_column(conn, table: str, col: str) -> bool:
            rows = conn.exec_driver_sql(f"PRAGMA table_info({table});").fetchall()
            return any(r[1] == col for r in rows)  # r[1] = name

        def _add_column(conn, table: str, ddl: str):
            conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {ddl}")

        with engine.begin() as conn:
            if not _has_column(conn, "quiz_sessions", "user_email"):
                _add_column(conn, "quiz_sessions", "user_email VARCHAR(320)")

            if not _has_column(conn, "emotion_events", "confidence_score"):
                _add_column(conn, "emotion_events", "confidence_score FLOAT")
    except Exception:
        # Never prevent startup/tests if migrations fail (best-effort).
        pass

if __name__ == "__main__":
    create_tables()
    print("Database tables created successfully!")
