import requests

url = 'http://localhost:8080/api/v1/quiz/generate'
payload = {
    'subject': 'mathématiques',
    'level': 'lycée',
    'num_questions': 3
}

resp = requests.post(url, json=payload)
print(resp.status_code)
print(resp.text)
