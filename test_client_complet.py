#!/usr/bin/env python3
"""
Test Client Complet SIMCO
Simule un utilisateur complet : quiz → résultats → SMS → agent intelligent
"""

import requests
import json
import time
from typing import Dict, Any

class SIMCOTestClient:
    def __init__(self):
        self.base_url = "http://127.0.0.1:8080"
        self.session_id = None
        self.user_phone = "+33775790537"  # Numéro du client
        
    def test_backend_health(self):
        """Test 1: Vérifier la santé du backend"""
        print("🔍 Test 1: Santé du Backend")
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Backend OK: {data}")
                return True
            else:
                print(f"❌ Backend erreur: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Backend inaccessible: {e}")
            return False
    
    def test_frontend_health(self):
        """Test 2: Vérifier le frontend"""
        print("\n🌐 Test 2: Santé du Frontend")
        try:
            response = requests.get("http://localhost:5173", timeout=5)
            if response.status_code == 200:
                print("✅ Frontend OK")
                return True
            else:
                print(f"❌ Frontend erreur: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Frontend inaccessible: {e}")
            return False
    
    def create_quiz_session(self):
        """Test 3: Créer une session quiz"""
        print("\n📝 Test 3: Création Session Quiz")
        try:
            session_data = {
                "user_name": "Test Client",
                "subject": "mathématiques",
                "level": "lycée",
                "student_id": "test_client_001"
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/quiz/sessions",
                json=session_data,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.session_id = data.get("id")
                print(f"✅ Session créée: ID {self.session_id}")
                return True
            else:
                print(f"❌ Erreur création session: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Exception création session: {e}")
            return False
    
    def generate_quiz_questions(self):
        """Test 4: Générer des questions quiz"""
        print("\n❓ Test 4: Génération Questions Quiz")
        try:
            quiz_data = {
                "subject": "mathématiques",
                "level": "lycée",
                "num_questions": 5
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/quiz/generate",
                json=quiz_data,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    quiz = data[0]
                    questions = quiz.get("questions", [])
                    print(f"✅ {len(questions)} questions générées")
                    return questions
                else:
                    print("❌ Aucune question générée")
                    return None
            else:
                print(f"❌ Erreur génération questions: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Exception génération questions: {e}")
            return None
    
    def submit_quiz_answers(self, questions):
        """Test 5: Soumettre des réponses"""
        print("\n✅ Test 5: Soumission Réponses")
        try:
            correct_count = 0
            for i, question in enumerate(questions[:3]):  # 3 questions seulement
                # Prendre la première option comme réponse
                options = question.get("choices", {})
                if options:
                    first_option = list(options.keys())[0]
                    
                    answer_data = {
                        "session_id": self.session_id,
                        "question_index": i,
                        "selected_answer": first_option,
                        "confidence_level": 0.8,
                        "response_time_ms": 5000
                    }
                    
                    response = requests.post(
                        f"{self.base_url}/api/v1/quiz/submit",
                        json=answer_data,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        is_correct = data.get("is_correct", False)
                        if is_correct:
                            correct_count += 1
                        print(f"  Question {i+1}: {'✅' if is_correct else '❌'}")
                    else:
                        print(f"  Question {i+1}: Erreur soumission")
            
            print(f"✅ Score: {correct_count}/3")
            return correct_count > 0
        except Exception as e:
            print(f"❌ Exception soumission: {e}")
            return False
    
    def test_sms_sending(self):
        """Test 6: Envoyer SMS au client"""
        print(f"\n📱 Test 6: Envoi SMS au {self.user_phone}")
        try:
            sms_data = {
                "session_id": self.session_id,
                "phone_number": self.user_phone
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/quiz/send-sms-report",
                json=sms_data,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print(f"✅ SMS envoyé à {self.user_phone}")
                    print(f"   Message: {data.get('message', 'Rapport envoyé')}")
                    return True
                else:
                    print(f"❌ Échec SMS: {data.get('message', 'Erreur inconnue')}")
                    return False
            else:
                print(f"❌ Erreur API SMS: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Exception SMS: {e}")
            return False
    
    def test_agent_fast_qcm(self):
        """Test 7: Génération QCM ultra-rapide"""
        print("\n⚡ Test 7: Génération QCM Ultra-Rapide")
        try:
            qcm_data = {
                "session_id": self.session_id,
                "num_questions": 5,
                "difficulty": "adaptive"
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/agent-fast/generate-qcm-instant",
                params=qcm_data,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    qcm = data.get("qcm", {})
                    questions = qcm.get("questions", [])
                    print(f"✅ QCM ultra-rapide généré: {len(questions)} questions")
                    print(f"   Difficulté: {qcm.get('difficulty')}")
                    print(f"   Temps génération: {qcm.get('generation_time')}")
                    return True
                else:
                    print(f"❌ Échec QCM: {data}")
                    return False
            else:
                print(f"❌ Erreur QCM: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Exception QCM: {e}")
            return False
    
    def test_agent_analysis(self):
        """Test 8: Analyse par agent intelligent"""
        print("\n🤖 Test 8: Analyse Agent Intelligent")
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/agent/analyze-results",
                params={"session_id": self.session_id},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    analysis = data.get("analysis", {})
                    score = analysis.get("score_percentage", 0)
                    print(f"✅ Analyse réussie:")
                    print(f"   Score: {score}%")
                    print(f"   Questions répondues: {analysis.get('total_questions', 0)}")
                    return True
                else:
                    print(f"❌ Échec analyse: {data}")
                    return False
            else:
                print(f"❌ Erreur analyse: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Exception analyse: {e}")
            return False
    
    def test_simple_qcm(self):
        """Test 9: QCM simple sans session"""
        print("\n📝 Test 9: QCM Simple (sans session)")
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/agent-fast/generate-qcm-simple",
                params={
                    "subject": "mathématiques",
                    "difficulty": "intermédiaire",
                    "num_questions": 3
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    qcm = data.get("qcm", {})
                    questions = qcm.get("questions", [])
                    print(f"✅ QCM simple généré: {len(questions)} questions")
                    return True
                else:
                    print(f"❌ Échec QCM simple: {data}")
                    return False
            else:
                print(f"❌ Erreur QCM simple: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Exception QCM simple: {e}")
            return False
    
    def run_complete_test(self):
        """Exécuter tous les tests"""
        print("🚀 DÉMARRAGE TEST COMPLET SIMCO")
        print("=" * 50)
        
        tests = [
            ("Backend Health", self.test_backend_health),
            ("Frontend Health", self.test_frontend_health),
            ("Session Quiz", self.create_quiz_session),
            ("Génération Questions", self.generate_quiz_questions),
            ("Soumission Réponses", self.submit_quiz_answers),
            ("Envoi SMS Client", self.test_sms_sending),
            ("QCM Ultra-Rapide", self.test_agent_fast_qcm),
            ("Agent Intelligent", self.test_agent_analysis),
            ("QCM Simple", self.test_simple_qcm)
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                start_time = time.time()
                success = test_func()
                end_time = time.time()
                duration = end_time - start_time
                
                results.append({
                    "test": test_name,
                    "success": success,
                    "duration": f"{duration:.2f}s"
                })
                
                print(f"   Durée: {duration:.2f}s")
                
                if not success and test_name in ["Backend Health", "Session Quiz"]:
                    print("⚠️ Test critique échoué, arrêt des tests")
                    break
                    
            except Exception as e:
                print(f"💥 Erreur inattendue dans {test_name}: {e}")
                results.append({
                    "test": test_name,
                    "success": False,
                    "error": str(e)
                })
            
            time.sleep(1)  # Pause entre tests
        
        # Résumé final
        print("\n" + "=" * 50)
        print("📊 RÉSUMÉ DES TESTS")
        print("=" * 50)
        
        success_count = 0
        for result in results:
            status = "✅" if result.get("success") else "❌"
            duration = result.get("duration", "N/A")
            print(f"{status} {result['test']:<25} ({duration})")
            if result.get("success"):
                success_count += 1
        
        print(f"\n🎯 Résultat: {success_count}/{len(results)} tests réussis")
        
        if success_count == len(results):
            print("🎉 TOUS LES TESTS RÉUSSIS ! SIMCO est prêt !")
        else:
            print("⚠️ Certains tests ont échoué - Vérifiez la configuration")
        
        return success_count == len(results)

if __name__ == "__main__":
    client = SIMCOTestClient()
    client.run_complete_test()
