import os
import re

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_simco.db")

from app.core.init_db import create_tables
create_tables()

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_generate_quiz_returns_questions_with_letters():
    payload = {
        "subject": "mathematiques",
        "level": "professionnel",
        "sector": "informatique_data",
        "difficulty": "medium",
        "num_questions": 5,
        "force_refresh": True,
        "country": "test",
        "class_level": "intermediaire",
    }

    res = client.post("/api/v1/quiz/generate", json=payload)
    assert res.status_code == 200

    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 1

    quiz = data[0]
    assert "questions" in quiz
    assert len(quiz["questions"]) == 5

    for q in quiz["questions"]:
        assert isinstance(q.get("choices"), list)
        assert len(q["choices"]) == 4
        assert q.get("correct_answer") in {"A", "B", "C", "D"}


def test_session_and_submit_answer_flow():
    gen_payload = {
        "subject": "chimie",
        "level": "universite",
        "sector": "sante",
        "difficulty": "easy",
        "num_questions": 3,
        "force_refresh": True,
        "country": "test",
        "class_level": "L1",
    }

    gen = client.post("/api/v1/quiz/generate", json=gen_payload)
    assert gen.status_code == 200

    quiz = gen.json()[0]

    sess = client.post(
        "/api/v1/quiz/sessions",
        json={
            "quiz_id": quiz["id"],
            "student_id": "student-1",
            "user_name": "student-1",
            "subject": gen_payload["subject"],
            "level": gen_payload["level"],
            "class_level": gen_payload["class_level"],
        },
    )
    assert sess.status_code == 200
    session_id = sess.json()["id"]

    submit = client.post(
        "/api/v1/quiz/submit",
        json={
            "session_id": session_id,
            "question_index": 0,
            "selected_answer": "A",
            "confidence_level": 0.5,
            "response_time_ms": 1234,
        },
    )
    assert submit.status_code == 200
    ans = submit.json()

    assert isinstance(ans.get("is_correct"), bool)
    assert ans.get("correct_answer") in {"A", "B", "C", "D"}

    report = client.get(f"/api/v1/quiz/sessions/{session_id}/report")
    assert report.status_code == 200
    rep = report.json()
    assert "biases" in rep
    assert "confidence" in rep
    assert "vector_d" in rep["confidence"]
    assert "vector_c" in rep["confidence"]

    pdf = client.get(f"/api/v1/quiz/sessions/{session_id}/report.pdf")
    assert pdf.status_code in (200, 501)
    if pdf.status_code == 200:
        assert pdf.headers.get("content-type", "").startswith("application/pdf")
