"""
migrate_data.py
Convert old session format to new training format
"""
import json
from pathlib import Path

def migrate_sessions():
    old_file = Path("data/training/sessions.jsonl")
    new_file = Path("data/training/sessions_new.jsonl")
    
    if not old_file.exists():
        print("No data to migrate")
        return
    
    samples_migrated = 0
    
    with open(old_file, "r", encoding="utf-8") as f_in, \
         open(new_file, "w", encoding="utf-8") as f_out:
        
        for line in f_in:
            session = json.loads(line)
            
            # Extract each question as a training sample
            for q in session.get("questions", []):
                if "features" in q and "behavioral_metrics" in q:
                    sample = {
                        "is_correct": q["features"]["is_correct"],
                        "confidence": q["features"]["confidence"],
                        "behavioral_metrics": q["behavioral_metrics"],
                        "features": q["features"]
                    }
                    f_out.write(json.dumps(sample) + "\n")
                    samples_migrated += 1
    
    # Backup old file and replace with new
    backup_file = Path("data/training/sessions_old_backup.jsonl")
    old_file.rename(backup_file)
    new_file.rename(old_file)
    
    print(f"✅ Migrated {samples_migrated} training samples")
    print(f"📦 Old data backed up to: {backup_file}")
    
    return samples_migrated

if __name__ == "__main__":
    migrate_sessions()
