# Notification Backend (FastAPI)

Dedicated FastAPI service to send quiz result notifications by email.

Each email includes a PDF attachment (`simco_result_report.pdf`) with statistics summary,
confidence metrics, recommendations, and per-question analysis (when provided).

## Endpoints

- `GET /health`
- `POST /notifications/quiz-result`

## Run

```bash
cd services/notification_backend
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8020 --reload
```

## SMTP Configuration

Create `.env` from `.env.example` and set:

- `MAIL_HOST=smtp.gmail.com`
- `MAIL_PORT=587`
- `MAIL_USERNAME=kamdem.guy@institutsaintjean.org`
- `MAIL_PASSWORD=<app-password>`
- `MAIL_STARTTLS=true`
- `MAIL_AUTH=true`

## Request Example

```json
{
  "user_name": "Guy",
  "user_email": "student@example.com",
  "quiz_result": {
    "score": 7,
    "total_questions": 10,
    "percentage": 70,
    "level": "Bien",
    "message": "Bonne performance",
    "recommendations": ["Réviser les erreurs", "Continuer la pratique"],
    "self_confidence": 65,
    "true_confidence": 58,
    "profile_label": "Sous-confiant"
  },
  "dunning_kruger": {
    "actual_score": 70,
    "declared_confidence": 65,
    "calibration_score": 78
  },
  "question_results": [
    {
      "question": "Question 1",
      "is_correct": true,
      "confidence_analysis": "Bonne réponse avec confiance élevée",
      "face_confidence": 72
    }
  ]
}
```
