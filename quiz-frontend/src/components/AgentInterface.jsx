import { useState, useEffect, useCallback } from 'react'

const API_BASE_URL = 'http://127.0.0.1:8080'

const AgentInterface = ({ sessionId, onBack }) => {
  const [activeTab, setActiveTab] = useState('analysis')
  const [loading, setLoading] = useState(false)
  const [analysis, setAnalysis] = useState(null)
  const [recommendations, setRecommendations] = useState(null)
  const [learningPlan, setLearningPlan] = useState(null)
  const [qcm, setQcm] = useState(null)
  const [profile, setProfile] = useState(null)
  const [progress, setProgress] = useState(null)
  const [error, setError] = useState(null)

  const loadAnalysis = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/agent/analyze-results?session_id=${sessionId}`)
      const data = await response.json()
      
      if (data.success) {
        setAnalysis(data.analysis)
      } else {
        setError('Erreur lors de l\'analyse')
      }
    } catch (error) {
      console.error('Error loading analysis:', error)
      setError('Erreur de connexion')
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  const loadProfile = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/agent/get-user-profile/${sessionId}`)
      const data = await response.json()
      if (data.success) {
        setProfile(data.profile)
      }
    } catch (error) {
      console.error('Error loading profile:', error)
    }
  }, [sessionId])

  const loadProgress = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/agent/get-learning-progress`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
      })
      const data = await response.json()
      if (data.success) {
        setProgress(data.progress)
      }
    } catch (error) {
      console.error('Error loading progress:', error)
    }
  }, [sessionId])

  // Charger l'analyse au démarrage
  useEffect(() => {
    if (sessionId) {
      loadAnalysis()
      loadProfile()
      loadProgress()
    }
  }, [sessionId, loadAnalysis, loadProfile, loadProgress])

  const loadRecommendations = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/agent/generate-recommendations?session_id=${sessionId}`)
      const data = await response.json()
      
      if (data.success) {
        setRecommendations(data.recommendations)
      } else {
        setError('Erreur lors de la génération des recommandations')
      }
    } catch (error) {
      console.error('Error loading recommendations:', error)
      setError('Erreur de connexion')
    } finally {
      setLoading(false)
    }
  }

  const loadLearningPlan = async (duration = 4) => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/agent/create-learning-plan?session_id=${sessionId}&duration_weeks=${duration}`)
      const data = await response.json()
      
      if (data.success) {
        setLearningPlan(data.learning_plan)
      } else {
        setError('Erreur lors de la création du plan d\'apprentissage')
      }
    } catch (error) {
      console.error('Error loading learning plan:', error)
      setError('Erreur de connexion')
    } finally {
      setLoading(false)
    }
  }

  const generatePersonalizedQCM = async (numQuestions = 10, difficulty = 'adaptive', useFastMode = true) => {
    setLoading(true)
    try {
      // Utiliser l'endpoint ultra-rapide par défaut
      const endpoint = useFastMode ? 'agent-fast' : 'agent'
      const url = useFastMode
        ? `${API_BASE_URL}/api/v1/${endpoint}/generate-qcm-instant?session_id=${sessionId}&num_questions=${numQuestions}&difficulty=${difficulty}`
        : `${API_BASE_URL}/api/v1/${endpoint}/generate-personalized-qcm?session_id=${sessionId}&num_questions=${numQuestions}&difficulty=${difficulty}`
      
      const response = await fetch(url)
      const data = await response.json()
      
      if (data.success) {
        setQcm(data.qcm)
        setActiveTab('qcm')
        
        // Afficher le mode utilisé
        if (useFastMode) {
          console.log('⚡ QCM généré en mode ULTRA-RAPIDE')
        }
      } else {
        setError('Erreur lors de la génération du QCM')
      }
    } catch (error) {
      console.error('Error generating QCM:', error)
      setError('Erreur de connexion')
    } finally {
      setLoading(false)
    }
  }

  const tabs = [
    { id: 'analysis', label: '📊 Analyse', icon: '🔍' },
    { id: 'recommendations', label: '💡 Recommandations', icon: '🎯' },
    { id: 'learning-plan', label: '📚 Plan Apprentissage', icon: '📅' },
    { id: 'qcm', label: '❓ QCM Personnalisé', icon: '📝' },
    { id: 'profile', label: '👤 Profil', icon: '📈' }
  ]

  const renderAnalysis = () => {
    if (!analysis) return <div className="text-center py-8">Chargement de l'analyse...</div>

    return (
      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-bold mb-4">📊 Performance Globale</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-3xl font-bold text-blue-600">{analysis.score_percentage}%</div>
              <div className="text-gray-600">Score global</div>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-3xl font-bold text-green-600">{analysis.correct_answers}/{analysis.total_questions}</div>
              <div className="text-gray-600">Réponses correctes</div>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <div className="text-3xl font-bold text-purple-600">{Object.keys(analysis.performance_by_topic || {}).length}</div>
              <div className="text-gray-600">Sujets analysés</div>
            </div>
          </div>

          <h4 className="text-lg font-semibold mb-3">Performance par Sujet</h4>
          <div className="space-y-2">
            {Object.entries(analysis.performance_by_topic || {}).map(([topic, score]) => (
              <div key={topic} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                <span className="font-medium">{topic}</span>
                <div className="flex items-center">
                  <div className="w-32 bg-gray-200 rounded-full h-2 mr-3">
                    <div 
                      className="bg-blue-600 h-2 rounded-full" 
                      style={{ width: `${score}%` }}
                    ></div>
                  </div>
                  <span className="font-bold">{Math.round(score)}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-bold mb-4">🧠 Analyse Détaillée</h3>
          <div className="prose max-w-none">
            <pre className="whitespace-pre-wrap text-gray-700">{analysis.detailed_analysis}</pre>
          </div>
        </div>
      </div>
    )
  }

  const renderRecommendations = () => {
    if (!recommendations) {
      return (
        <div className="text-center py-8">
          <button
            onClick={loadRecommendations}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-bold py-3 px-6 rounded-lg"
          >
            {loading ? 'Génération en cours...' : 'Générer les recommandations'}
          </button>
        </div>
      )
    }

    return (
      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-bold mb-4">💡 Recommandations Personnalisées</h3>
          <div className="prose max-w-none">
            <pre className="whitespace-pre-wrap text-gray-700">{recommendations.recommendations}</pre>
          </div>
        </div>

        {recommendations.priority_topics && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-xl font-bold mb-4">🎯 Sujets Prioritaires</h3>
            <div className="flex flex-wrap gap-2">
              {recommendations.priority_topics.map((topic, index) => (
                <span key={index} className="bg-red-100 text-red-800 px-3 py-1 rounded-full text-sm font-medium">
                  {topic}
                </span>
              ))}
            </div>
          </div>
        )}

        {recommendations.learning_resources && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-xl font-bold mb-4">📚 Ressources Recommandées</h3>
            <div className="space-y-3">
              {recommendations.learning_resources.map((resource, index) => (
                <div key={index} className="border-l-4 border-blue-500 pl-4 py-2">
                  <div className="font-medium">{resource.title}</div>
                  <div className="text-sm text-gray-600">
                    Type: {resource.type} | Durée: {resource.estimated_time}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {recommendations.study_techniques && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-xl font-bold mb-4">🛠️ Techniques d'Étude</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {recommendations.study_techniques.map((technique, index) => (
                <div key={index} className="bg-green-50 p-3 rounded-lg">
                  <div className="font-medium text-green-800">✓ {technique}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  const renderLearningPlan = () => {
    if (!learningPlan) {
      return (
        <div className="text-center py-8">
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Durée du plan (semaines)
            </label>
            <select
              className="border border-gray-300 rounded-lg px-3 py-2"
              onChange={(e) => loadLearningPlan(parseInt(e.target.value))}
            >
              <option value="2">2 semaines</option>
              <option value="4">4 semaines</option>
              <option value="8">8 semaines</option>
              <option value="12">12 semaines</option>
            </select>
          </div>
          <button
            onClick={() => loadLearningPlan(4)}
            disabled={loading}
            className="bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-bold py-3 px-6 rounded-lg"
          >
            {loading ? 'Création en cours...' : 'Créer le plan d\'apprentissage'}
          </button>
        </div>
      )
    }

    return (
      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-bold mb-4">📅 Plan d'Apprentissage Personnalisé</h3>
          <div className="prose max-w-none">
            <pre className="whitespace-pre-wrap text-gray-700">{learningPlan.plan}</pre>
          </div>
        </div>

        {learningPlan.weekly_goals && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-xl font-bold mb-4">📋 Objectifs Hebdomadaires</h3>
            <div className="space-y-3">
              {learningPlan.weekly_goals.map((goal, index) => (
                <div key={index} className="border-l-4 border-green-500 pl-4 py-2">
                  <div className="font-medium">Semaine {goal.week}</div>
                  <div className="text-sm text-gray-600">
                    Sujets: {goal.topics?.join(', ') || 'Révision générale'}
                  </div>
                  <div className="text-sm text-gray-600">
                    Exercices: {goal.exercises_count} | Heures: {goal.study_hours}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {learningPlan.milestones && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-xl font-bold mb-4">🎯 Jalons d'Apprentissage</h3>
            <div className="space-y-3">
              {learningPlan.milestones.map((milestone, index) => (
                <div key={index} className="bg-blue-50 p-4 rounded-lg">
                  <div className="font-medium text-blue-800">
                    Semaine {milestone.week}: {milestone.title}
                  </div>
                  <div className="text-sm text-blue-600">
                    {milestone.goals?.join(', ') || 'Révision et pratique'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  const renderQCM = () => {
    if (!qcm) {
      return (
        <div className="text-center py-8">
          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-4">⚡ Génération Rapide de QCM</h3>
            
            {/* Boutons prédéfinis - MODE ULTRA-RAPIDE */}
            <div className="mb-6">
              <h4 className="text-lg font-semibold mb-3 text-green-600">⚡ MODE ULTRA-RAPIDE (sans LLM)</h4>
              <div className="grid grid-cols-3 gap-3">
                <button
                  onClick={() => generatePersonalizedQCM(5, 'débutant', true)}
                  disabled={loading}
                  className={`p-4 rounded-lg text-center transition-all transform hover:scale-105 ${
                    loading ? 'bg-gray-200 cursor-not-allowed' :
                    'bg-green-500 hover:bg-green-600 text-white shadow-lg'
                  }`}
                >
                  <div className="text-2xl mb-2">⚡</div>
                  <div className="font-semibold">Ultra-Rapide</div>
                  <div className="text-sm">5 questions</div>
                  <div className="text-xs opacity-75">Instantané</div>
                </button>
                
                <button
                  onClick={() => generatePersonalizedQCM(10, 'adaptive', true)}
                  disabled={loading}
                  className={`p-4 rounded-lg text-center transition-all transform hover:scale-105 ${
                    loading ? 'bg-gray-200 cursor-not-allowed' :
                    'bg-blue-500 hover:bg-blue-600 text-white shadow-lg'
                  }`}
                >
                  <div className="text-2xl mb-2">🚀</div>
                  <div className="font-semibold">Adaptatif</div>
                  <div className="text-sm">10 questions</div>
                  <div className="text-xs opacity-75">Ultra-fast</div>
                </button>
                
                <button
                  onClick={() => generatePersonalizedQCM(15, 'avancé', true)}
                  disabled={loading}
                  className={`p-4 rounded-lg text-center transition-all transform hover:scale-105 ${
                    loading ? 'bg-gray-200 cursor-not-allowed' :
                    'bg-purple-500 hover:bg-purple-600 text-white shadow-lg'
                  }`}
                >
                  <div className="text-2xl mb-2">�</div>
                  <div className="font-semibold">Expert</div>
                  <div className="text-sm">15 questions</div>
                  <div className="text-xs opacity-75">Ultra-fast</div>
                </button>
              </div>
            </div>

            {/* Séparateur */}
            <div className="border-t pt-4 mb-4">
              <div className="text-center text-gray-500 text-sm">--- Ou mode classique avec LLM ---</div>
            </div>

            {/* Options rapides en grille */}
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  📝 Nombre de questions
                </label>
                <div className="flex gap-2">
                  {[5, 10, 15, 20].map(num => (
                    <button
                      key={num}
                      onClick={() => generatePersonalizedQCM(num, 'adaptive', false)}
                      disabled={loading}
                      className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                        loading ? 'bg-gray-300 cursor-not-allowed' :
                        'bg-blue-600 hover:bg-blue-700 text-white'
                      }`}
                    >
                      {num}
                    </button>
                  ))}
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  🎯 Difficulté
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => generatePersonalizedQCM(10, 'adaptive', false)}
                    disabled={loading}
                    className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      loading ? 'bg-gray-300 cursor-not-allowed' :
                      'bg-green-600 hover:bg-green-700 text-white'
                    }`}
                  >
                    ⚡ Adaptative
                  </button>
                  <button
                    onClick={() => generatePersonalizedQCM(10, 'intermédiaire', false)}
                    disabled={loading}
                    className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      loading ? 'bg-gray-300 cursor-not-allowed' :
                      'bg-yellow-600 hover:bg-yellow-700 text-white'
                    }`}
                  >
                    📚 Intermédiaire
                  </button>
                </div>
              </div>
            </div>

            {/* Options manuelles (avancé) */}
            <details className="text-left">
              <summary className="cursor-pointer text-gray-600 hover:text-gray-800 mb-4">
                ⚙️ Options avancées
              </summary>
              <div className="bg-gray-50 p-4 rounded-lg space-y-3">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Nombre personnalisé
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="50"
                      defaultValue="10"
                      className="border border-gray-300 rounded-lg px-3 py-2 w-full"
                      id="customNumQuestions"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Difficulté personnalisée
                    </label>
                    <select
                      className="border border-gray-300 rounded-lg px-3 py-2 w-full"
                      id="customDifficulty"
                    >
                      <option value="débutant">🌱 Débutant</option>
                      <option value="intermédiaire">📚 Intermédiaire</option>
                      <option value="avancé">🚀 Avancé</option>
                      <option value="expert">🏆 Expert</option>
                    </select>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      const numQuestions = parseInt(document.getElementById('customNumQuestions').value) || 10
                      const difficulty = document.getElementById('customDifficulty').value
                      generatePersonalizedQCM(numQuestions, difficulty, true)
                    }}
                    disabled={loading}
                    className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-bold py-3 px-6 rounded-lg"
                  >
                    ⚡ Générer (Ultra-Rapide)
                  </button>
                  <button
                    onClick={() => {
                      const numQuestions = parseInt(document.getElementById('customNumQuestions').value) || 10
                      const difficulty = document.getElementById('customDifficulty').value
                      generatePersonalizedQCM(numQuestions, difficulty, false)
                    }}
                    disabled={loading}
                    className="flex-1 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white font-bold py-3 px-6 rounded-lg"
                  >
                    🤖 Générer (LLM)
                  </button>
                </div>
              </div>
            </details>
          </div>

          {/* Indicateur de chargement */}
          {loading && (
            <div className="mt-6 p-4 bg-blue-50 rounded-lg text-center">
              <div className="flex items-center justify-center space-x-3">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                <span className="text-blue-800 font-medium">🤖 L'agent génère votre QCM personnalisé...</span>
              </div>
              <div className="text-sm text-blue-600 mt-2">
                Analyse de votre profil • Identification des sujets faibles • Génération adaptative
              </div>
            </div>
          )}
        </div>
      )
    }

    return (
      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-bold mb-4">📝 QCM Personnalisé</h3>
          <div className="mb-4 p-4 bg-blue-50 rounded-lg">
            <div className="text-sm text-blue-800">
              <strong>Niveau de personnalisation:</strong> {qcm.personalization_level}
            </div>
            <div className="text-sm text-blue-800">
              <strong>Difficulté:</strong> {qcm.difficulty}
            </div>
            <div className="text-sm text-blue-800">
              <strong>Sujets ciblés:</strong> {qcm.target_topics?.join(', ') || 'Général'}
            </div>
          </div>
          
          <div className="space-y-6">
            {qcm.questions?.map((question) => (
              <div key={question.id} className="border-l-4 border-purple-500 pl-4 py-4">
                <div className="font-medium mb-3">
                  Question {question.id}: {question.question}
                </div>
                <div className="space-y-2 ml-4">
                  {question.options?.map((option, optIndex) => (
                    <div key={optIndex} className={`p-2 rounded ${
                      question.correct_answer === option.charAt(0) 
                        ? 'bg-green-100 border-green-300 border' 
                        : 'bg-gray-50 border-gray-200 border'
                    }`}>
                      {option}
                    </div>
                  ))}
                </div>
                <div className="mt-3 p-3 bg-yellow-50 rounded text-sm">
                  <strong>Explication:</strong> {question.explanation}
                </div>
                <div className="text-xs text-gray-600 mt-2">
                  Concept: {question.concept} | Niveau: {question.bloom_level}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  const renderProfile = () => {
    if (!profile) return <div className="text-center py-8">Chargement du profil...</div>

    return (
      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-bold mb-4">👤 Profil d'Apprentissage</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-semibold mb-3">Informations Générales</h4>
              <div className="space-y-2">
                <div><strong>Nom:</strong> {profile.user_name}</div>
                <div><strong>Sessions:</strong> {profile.total_sessions}</div>
                <div><strong>Score moyen:</strong> {profile.average_score}%</div>
                <div><strong>Sujets étudiés:</strong> {profile.subjects_studied?.join(', ')}</div>
              </div>
            </div>
            <div>
              <h4 className="font-semibold mb-3">Statistiques</h4>
              <div className="space-y-2">
                <div><strong>Questions répondues:</strong> {profile.total_questions_answered}</div>
                <div><strong>Réponses correctes:</strong> {profile.total_correct_answers}</div>
                <div><strong>Sujet préféré:</strong> {profile.preferred_subject}</div>
                <div><strong>Dernière activité:</strong> {new Date(profile.last_activity).toLocaleDateString()}</div>
              </div>
            </div>
          </div>
        </div>

        {progress && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-xl font-bold mb-4">📈 Progrès d'Apprentissage</h3>
            <div className="mb-4">
              <div className="text-lg font-medium">
                Tendance: <span className={`font-bold ${
                  progress.trend === 'improving' ? 'text-green-600' : 
                  progress.trend === 'declining' ? 'text-red-600' : 'text-yellow-600'
                }`}>
                  {progress.trend === 'improving' ? '📈 Amélioration' : 
                   progress.trend === 'declining' ? '📉 Baisse' : '➡️ Stable'}
                </span>
              </div>
            </div>
            <div className="space-y-3">
              {progress.progress?.slice(-5).reverse().map((session, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                  <div>
                    <div className="font-medium">{session.subject}</div>
                    <div className="text-sm text-gray-600">
                      {new Date(session.date).toLocaleDateString()}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-lg">{session.score}%</div>
                    <div className="text-sm text-gray-600">
                      {session.correct_answers}/{session.total_questions}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 p-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">🤖 Agent Intelligent SIMCO</h1>
              <p className="text-gray-600">
                Analyse • Recommandations • Plan d'apprentissage • QCM personnalisé
              </p>
            </div>
            <button
              onClick={onBack}
              className="bg-gray-600 hover:bg-gray-700 text-white font-medium py-2 px-4 rounded-lg"
            >
              ← Retour
            </button>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Loading Overlay */}
        {loading && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <div className="text-gray-700">Traitement en cours...</div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow-md mb-6">
          <div className="flex space-x-1 p-1">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 py-3 px-4 rounded-lg font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        <div className="bg-white rounded-lg shadow-md p-6">
          {activeTab === 'analysis' && renderAnalysis()}
          {activeTab === 'recommendations' && renderRecommendations()}
          {activeTab === 'learning-plan' && renderLearningPlan()}
          {activeTab === 'qcm' && renderQCM()}
          {activeTab === 'profile' && renderProfile()}
        </div>
      </div>
    </div>
  )
}

export default AgentInterface
