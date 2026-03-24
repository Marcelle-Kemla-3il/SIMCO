import requests
import json

# Test 1: Generate a single question with answers
print("=== TEST 1: Generate Question with Options ===")
url = "http://localhost:8000/generate-question"
payload = {
    "subject": "mathématiques",
    "level": "lycée",
    "user_info": "L'utilisateur a de bonnes bases en algèbre."
}
response = requests.post(url, json=payload)
data = response.json()
print(f"Session ID: {data.get('session_id')}")
print(f"Question ID: {data.get('question_id')}")
print(f"Question: {data.get('question')}")
print("Options:")
for i, option in enumerate(data.get('options', [])):
    print(f"  {chr(65+i)}) {option}")
print(f"Explication: {data.get('explanation')}\n")

# Store session and question IDs for testing
session_id = data.get('session_id')
question_id = data.get('question_id')

# Test 2: Submit an answer
print("=== TEST 2: Submit Answer ===")
answer_url = "http://localhost:8000/submit-answer"
answer_payload = {
    "session_id": session_id,
    "question_id": question_id,
    "selected_answer": 0  # Selecting option A
}
answer_response = requests.post(answer_url, json=answer_payload)
answer_data = answer_response.json()
print(f"Correct: {answer_data.get('correct')}")
print(f"Correct Answer Index: {answer_data.get('correct_answer')}")
print(f"Explanation: {answer_data.get('explanation')}")
print(f"Current Score: {answer_data.get('score')}/{answer_data.get('total_questions')}\n")

# Test 3: Get quiz score
print("=== TEST 3: Get Quiz Score ===")
score_url = f"http://localhost:8000/quiz-score/{session_id}"
score_response = requests.get(score_url)
score_data = score_response.json()
print(f"Score: {score_data.get('score')}/{score_data.get('total_questions')}")
print(f"Percentage: {score_data.get('percentage')}%")
print(f"Questions Answered: {score_data.get('answered')}\n")

# Test 4: Generate a complete quiz (multiple questions)
print("=== TEST 4: Generate Complete Quiz (3 questions) ===")
quiz_url = "http://localhost:8000/generate-quiz?num_questions=3"
quiz_payload = {
    "subject": "histoire",
    "level": "collège",
    "user_info": ""
}
quiz_response = requests.post(quiz_url, json=quiz_payload)
quiz_data = quiz_response.json()
print(f"Quiz Session ID: {quiz_data.get('session_id')}")
print(f"Total Questions: {quiz_data.get('total_questions')}")
print("\nQuestions:")
for idx, q in enumerate(quiz_data.get('questions', []), 1):
    print(f"\n{idx}. {q.get('question')}")
    for i, opt in enumerate(q.get('options', [])):
        print(f"   {chr(65+i)}) {opt}")
