# SIMCO Logic

FastAPI project scaffold.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

   pip install -r requirements.txt

## Run

From this folder:

uvicorn app.main:app --reload --host 0.0.0.0 --port 8010

## Endpoints

- `GET /` - welcome message
- `GET /health` - health check
- `POST /analyze/true-confidence` - predict true confidence from quiz self-confidence + per-question face confidences

### Example request

{
   "self_confidence": 71,
   "face_confidence_per_question": [0.65, 0.65, 0.53, 0.65]
}

### Example response

{
   "true_confidence_normalized": 0.67,
   "true_confidence": 67.0,
   "input_summary": {
      "self_confidence_normalized": 0.71,
      "questions_count": 4
   },
   "model": "numpy_mlp_regressor"
}
