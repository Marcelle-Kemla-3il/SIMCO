Question banks JSON format

Each JSON file contains an object with a single key "questions" which is a list of questions.

Question schema:
{
  "question": "...",
  "choices": ["...", "...", "...", "..."],
  "correct_answer": "A" | "B" | "C" | "D",
  "explanation": "...",
  "difficulty": "easy" | "medium" | "hard"
}

Path conventions:
- Lycee: app/data/question_banks/lycee/<subject>/<class_level>.json
- Universite: app/data/question_banks/universite/math/<class_level>.json  (class_level in L1..M2)
- Pro: app/data/question_banks/pro/<sector>/<subject>.json  (subject can be informatique/business/sante)

The loader will:
- select by (level, subject, class_level, sector)
- filter by difficulty, and if not enough questions, expand to other difficulties
- ensure uniqueness by question text
- require at least 30 unique questions per bank file
