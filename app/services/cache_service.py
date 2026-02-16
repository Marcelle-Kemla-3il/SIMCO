import json
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

class CacheService:
    def __init__(self):
        self.cache = {}
        self.cache_duration = timedelta(minutes=2)  # Cache pendant 2 minutes only
    
    def _time_bucket(self) -> str:
        """Bucket de temps pour éviter la répétition prolongée (rafraîchit ~2 min)."""
        now = datetime.now()
        bucket_minute = (now.minute // 2) * 2  # tranches de 2 minutes
        return now.strftime(f"%Y%m%d%H{bucket_minute:02d}")

    def _generate_cache_key(self, subject: str, level: str, num_questions: int, topics: Optional[list] = None) -> str:
        """Générer une clé de cache unique incluant un bucket temporel et les topics."""
        topics_repr = ",".join(topics) if topics else "-"
        # Add random salt for more variation when force_refresh is True
        import random
        random_salt = random.randint(1, 100)
        key_data = f"{subject}_{level}_{num_questions}_{topics_repr}_{self._time_bucket()}_{random_salt}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get_cached_quiz(self, subject: str, level: str, num_questions: int, topics: Optional[list] = None) -> Optional[List[Dict[str, Any]]]:
        """Récupérer un quiz depuis le cache"""
        cache_key = self._generate_cache_key(subject, level, num_questions, topics)
        
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            
            # Vérifier si le cache est encore valide
            if datetime.now() - cached_data['timestamp'] < self.cache_duration:
                print(f"DEBUG: Cache hit for {subject} {level} {num_questions}")
                return cached_data['questions']
            else:
                # Cache expiré, le supprimer
                del self.cache[cache_key]
        
        return None
    
    def cache_quiz(self, subject: str, level: str, num_questions: int, questions: List[Dict[str, Any]], topics: Optional[list] = None):
        """Mettre en cache un quiz"""
        cache_key = self._generate_cache_key(subject, level, num_questions, topics)
        
        self.cache[cache_key] = {
            'questions': questions,
            'timestamp': datetime.now()
        }
        print(f"DEBUG: Cached quiz for {subject} {level} {num_questions}")
    
    def clear_cache(self):
        """Vider tout le cache"""
        self.cache.clear()
        print("DEBUG: Cache cleared")

# Instance globale du cache
cache_service = CacheService()
