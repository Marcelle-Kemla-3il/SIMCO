import { useState, useEffect, useRef } from 'react'
import QuizInterfacePage from './QuizInterfacePage'
import DunningKrugerChart from './DunningKrugerChart'
import { usePhotoCapture } from '../hooks/usePhotoCapture'

const API_BASE_URL = 'http://localhost:8000'

function QuizPage({ onBackToHome }) {
  const [currentStep, setCurrentStep] = useState(1)
  const [userName, setUserName] = useState('')
  const [userAge, setUserAge] = useState('')
  const [userAcademicLevel, setUserAcademicLevel] = useState('lycée')
  const [userEmail, setUserEmail] = useState('')
  const [subject, setSubject] = useState('mathématiques')
  const [level, setLevel] = useState('lycée')
  const [userInfo, setUserInfo] = useState('')
  const [questions, setQuestions] = useState([])
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [question, setQuestion] = useState(null)
  const [loading, setLoading] = useState(false)
  const [confidence, setConfidence] = useState(50)
  const [selectedOption, setSelectedOption] = useState(null)
  const [sessionId, setSessionId] = useState(null)
  const [showResults, setShowResults] = useState(false)
  const [results, setResults] = useState(null)
  const [answers, setAnswers] = useState([])
  const [timeRemaining, setTimeRemaining] = useState(1200)
  const [testStarted, setTestStarted] = useState(false)
  const [testEnded, setTestEnded] = useState(false)
  const timerRef = useRef(null)
  const [interactionData, setInteractionData] = useState(null)
  const [showReadyScreen, setShowReadyScreen] = useState(false)
  const [showCountdown, setShowCountdown] = useState(false)
  const [countdownValue, setCountdownValue] = useState(5)
  const [showFullscreenWarning, setShowFullscreenWarning] = useState(false)
  const [fullscreenWarningTime, setFullscreenWarningTime] = useState(10)
  const fullscreenWarningTimerRef = useRef(null)
  const [showConfidenceModal, setShowConfidenceModal] = useState(false)

  const [notions, setNotions] = useState(null)
  const [notionsLoading, setNotionsLoading] = useState(false)
  const [emailSending, setEmailSending] = useState(false)
  const [emailSent, setEmailSent] = useState(false)
  const [emailError, setEmailError] = useState('')
  const [reportEmail, setReportEmail] = useState('')
  const [showEmailModal, setShowEmailModal] = useState(false)

  const { videoRef, startCamera, stopCamera, startQuestion, captureOnAnswer } = usePhotoCapture(sessionId)

  useEffect(() => {
    if (testStarted && !testEnded) {
      const handleFullscreenChange = () => {
        if (!document.fullscreenElement) {
          if (fullscreenWarningTimerRef.current) clearInterval(fullscreenWarningTimerRef.current)
          setShowFullscreenWarning(true)
          setFullscreenWarningTime(10)
          let countdown = 10
          fullscreenWarningTimerRef.current = setInterval(() => {
            countdown--
            setFullscreenWarningTime(countdown)
            if (countdown <= 0) {
              clearInterval(fullscreenWarningTimerRef.current)
              endTest('Vous n\'avez pas repris le mode plein écran. Le test est terminé.')
            }
          }, 1000)
        } else {
          setShowFullscreenWarning(false)
          if (fullscreenWarningTimerRef.current) {
            clearInterval(fullscreenWarningTimerRef.current)
            fullscreenWarningTimerRef.current = null
          }
        }
      }
      document.addEventListener('fullscreenchange', handleFullscreenChange)
      document.addEventListener('webkitfullscreenchange', handleFullscreenChange)
      return () => {
        document.removeEventListener('fullscreenchange', handleFullscreenChange)
        document.removeEventListener('webkitfullscreenchange', handleFullscreenChange)
        if (fullscreenWarningTimerRef.current) clearInterval(fullscreenWarningTimerRef.current)
      }
    }
  }, [testStarted, testEnded])

  useEffect(() => {
    if (testStarted && !testEnded && timeRemaining > 0 && !showFullscreenWarning) {
      timerRef.current = setInterval(() => {
        setTimeRemaining((prev) => {
          if (prev <= 1) { endTest('Le temps est écoulé !'); return 0 }
          return prev - 1
        })
      }, 1000)
      return () => { if (timerRef.current) clearInterval(timerRef.current) }
    } else if (showFullscreenWarning && timerRef.current) {
      clearInterval(timerRef.current)
    }
  }, [testStarted, testEnded, timeRemaining, showFullscreenWarning])

  useEffect(() => {
    if (testStarted && questions.length > 0 && questions[0]) {
      startQuestion(questions[0].id, 120000)
    }
  }, [testStarted])

  useEffect(() => {
    return () => {
      if (fullscreenWarningTimerRef.current) clearInterval(fullscreenWarningTimerRef.current)
      stopCamera()
    }
  }, [])

  const fetchNotions = async () => {
    setNotionsLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/analyze-notions/${sessionId}`)
      const data = await res.json()
      if (data.success) setNotions(data)
    } catch (err) {
      console.error('Erreur notions:', err)
    } finally {
      setNotionsLoading(false)
    }
  }

  const handleDownloadPDF = async () => {
    try {
      const params = new URLSearchParams({ student_name: userName || 'Étudiant', subject })
      const res = await fetch(`${API_BASE_URL}/generate-report/${sessionId}?${params}`)
      if (!res.ok) throw new Error('Erreur PDF')
      const blob = await res.blob()
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href = url
      a.download = `rapport_SIMCO_${userName || 'etudiant'}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      alert('Erreur lors de la génération du PDF. Vérifiez que reportlab est installé.')
    }
  }

  const handleSendEmail = async () => {
    if (!reportEmail || !reportEmail.includes('@')) { setEmailError('Adresse email invalide'); return }
    setEmailSending(true)
    setEmailError('')
    try {
      const res = await fetch(`${API_BASE_URL}/send-report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, student_name: userName || 'Étudiant', student_email: reportEmail, subject })
      })
      const data = await res.json()
      if (data.success) { setEmailSent(true); setShowEmailModal(false) }
      else setEmailError(data.message || 'Erreur envoi email')
    } catch (err) {
      setEmailError('Erreur de connexion au serveur')
    } finally {
      setEmailSending(false)
    }
  }

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const endTest = (message) => {
    setTestEnded(true); setTestStarted(false)
    if (timerRef.current) clearInterval(timerRef.current)
    stopCamera()
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {})
    alert(message)
  }

  const handleUserInfoSubmit = (e) => { e.preventDefault(); setCurrentStep(2) }
  const handlePreferencesSubmit = () => setCurrentStep(3)
  const startTest = async () => await generateQuestions()

  const generateQuestions = async () => {
    setLoading(true); setCurrentStep(4)
    try {
      const response = await fetch(`${API_BASE_URL}/generate-quiz?num_questions=10`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subject, level, user_info: userInfo })
      })
      if (!response.ok) throw new Error('Failed')
      const data = await response.json()
      const formatted = data.questions.map(q => ({
        id: q.id, question: q.question,
        options: q.options.map((opt, idx) => ({ id: String.fromCharCode(65 + idx), text: opt }))
      }))
      setQuestions(formatted); setQuestion(formatted[0]); setSessionId(data.session_id); setShowReadyScreen(true)
    } catch (err) { alert('Erreur génération quiz.'); setCurrentStep(3) }
    finally { setLoading(false) }
  }

  const userClickedStart = async () => {
    try { await document.documentElement.requestFullscreen() } catch (e) {}
    setShowReadyScreen(false); setShowCountdown(true); setCountdownValue(5)
    const interval = setInterval(() => {
      setCountdownValue((prev) => {
        if (prev <= 1) { clearInterval(interval); setShowCountdown(false); setTestStarted(true); startCamera(); return 0 }
        return prev - 1
      })
    }, 1000)
  }

  const submitAnswer = async () => {
    if (selectedOption === null) { alert('Veuillez sélectionner une réponse.'); return }
    setLoading(true)
    const currentQ = questions[currentQuestionIndex]
    captureOnAnswer(currentQ.id)
    try {
      const answerIndex = selectedOption.charCodeAt(0) - 65
      const response = await fetch(`${API_BASE_URL}/submit-answer`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, question_id: currentQ.id, selected_answer: answerIndex, confidence: 50, behavioral_data: interactionData ? { interaction: interactionData } : {} })
      })
      if (!response.ok) throw new Error('Failed')
      const data = await response.json()
      setAnswers([...answers, { questionIndex: currentQuestionIndex, selectedOption, isCorrect: data.correct }])
      if (currentQuestionIndex < questions.length - 1) {
        const nextIndex = currentQuestionIndex + 1
        setCurrentQuestionIndex(nextIndex); setQuestion(questions[nextIndex]); setSelectedOption(null); setInteractionData(null)
        startQuestion(questions[nextIndex].id, 120000)
      } else { setShowConfidenceModal(true) }
    } catch (err) { alert('Erreur soumission.') }
    finally { setLoading(false) }
  }

  const submitAnswerWithConfidence = async () => {
    setShowConfidenceModal(false); setLoading(true)
    try {
      await fetch(`${API_BASE_URL}/update-confidence`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, confidence })
      })
      const res  = await fetch(`${API_BASE_URL}/quiz-results/${sessionId}`)
      const data = await res.json()
      setResults(data); setShowResults(true); setTestStarted(false); setTestEnded(true)
      stopCamera()
      if (document.fullscreenElement) document.exitFullscreen().catch(() => {})
      if (timerRef.current) clearInterval(timerRef.current)
    } catch (err) { alert('Erreur résultats.') }
    finally { setLoading(false) }
  }

  // ─── RENDER ──────────────────────────────────────────────────────────────

  if (currentStep === 4 && !testEnded && !showResults) {
    if (showReadyScreen) {
      return (
        <div className="h-screen flex items-center justify-center bg-gradient-to-br from-primary-900 via-primary-800 to-primary-900">
          <div className="text-center max-w-2xl mx-auto px-6">
            <h2 className="text-4xl font-bold text-white mb-4">Questions prêtes !</h2>
            <p className="text-primary-200 text-lg mb-8">Votre quiz de {questions.length} questions est prêt.</p>
            <div className="bg-white bg-opacity-10 rounded-xl p-6 mb-8 text-left">
              <ul className="text-primary-100 text-sm space-y-2">
                <li>• Mode plein écran obligatoire</li>
                <li>• 20 minutes pour répondre</li>
                <li>• 📷 Caméra activée pour analyser votre confiance</li>
              </ul>
            </div>
            <button onClick={userClickedStart} className="bg-white text-primary-900 font-bold py-4 px-12 rounded-xl text-lg">
              Commencer le quiz
            </button>
          </div>
        </div>
      )
    }
    if (showCountdown) {
      return (
        <div className="h-screen flex items-center justify-center bg-gradient-to-br from-primary-900 via-primary-800 to-primary-900">
          <div className="text-center">
            <h2 className="text-4xl font-bold text-white mb-8">Préparez-vous !</h2>
            <div className="text-9xl font-bold text-white mb-8">{countdownValue}</div>
          </div>
        </div>
      )
    }
    if (loading || !question) {
      return (
        <div className="h-screen flex items-center justify-center bg-gradient-to-br from-primary-900 via-primary-800 to-primary-900">
          <div className="text-center">
            <div className="w-32 h-32 border-8 border-primary-300 border-t-transparent rounded-full animate-spin mx-auto mb-6"></div>
            <h2 className="text-3xl font-bold text-white">Génération du quiz...</h2>
          </div>
        </div>
      )
    }
    return (
      <>
        <QuizInterfacePage subject={subject} timeRemaining={timeRemaining} formatTime={formatTime}
          question={question} selectedOption={selectedOption} setSelectedOption={setSelectedOption}
          submitAnswer={submitAnswer} loading={loading} currentQuestion={currentQuestionIndex + 1}
          totalQuestions={questions.length} onInteractionData={setInteractionData} videoRef={videoRef} />
        {showFullscreenWarning && (
          <div className="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center z-50">
            <div className="bg-white rounded-2xl p-8 max-w-md w-full text-center">
              <h3 className="text-2xl font-bold text-gray-900 mb-4">Attention !</h3>
              <p className="text-gray-700 mb-6">Revenez en plein écran dans :</p>
              <div className="text-6xl font-bold text-red-600 mb-6">{fullscreenWarningTime}</div>
              <button onClick={async () => { try { await document.documentElement.requestFullscreen() } catch(e){} }}
                className="bg-primary-600 text-white font-bold py-3 px-6 rounded-lg">Revenir en plein écran</button>
            </div>
          </div>
        )}
        {showConfidenceModal && (
          <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl p-8 max-w-lg w-full shadow-2xl">
              <div className="text-center mb-6">
                <h3 className="text-2xl font-bold text-gray-900 mb-1">Quiz terminé !</h3>
                <p className="text-gray-500 text-sm">Dernière étape avant vos résultats</p>
              </div>
              <p className="text-center text-gray-800 font-medium mb-6">Quel était votre niveau de confiance global ?</p>
              <div className="mb-6">
                <div className="text-center mb-4">
                  <span className="text-6xl font-bold" style={{ color: confidence >= 70 ? '#16a34a' : confidence >= 40 ? '#d97706' : '#dc2626' }}>{confidence}%</span>
                </div>
                <input type="range" min="0" max="100" value={confidence}
                  onChange={(e) => setConfidence(Number(e.target.value))}
                  className="w-full h-4 rounded-lg appearance-none cursor-pointer mb-3"
                  style={{ background: `linear-gradient(to right, ${confidence >= 70 ? '#16a34a' : confidence >= 40 ? '#d97706' : '#dc2626'} ${confidence}%, #e5e7eb ${confidence}%)` }} />
                <div className="flex justify-between text-xs text-gray-400"><span>0%</span><span>50%</span><span>100%</span></div>
              </div>
              <button onClick={submitAnswerWithConfidence} className="w-full bg-gradient-to-r from-primary-600 to-primary-700 text-white font-bold py-4 rounded-xl">
                Voir mes résultats →
              </button>
            </div>
          </div>
        )}
      </>
    )
  }

  // ─── RESULTS PAGE ──────────────────────────────────────────────────────────
  if (showResults && results) {
    const scoreEmoji = results.percentage >= 80 ? '🏆' : results.percentage >= 60 ? '🎯' : results.percentage >= 40 ? '💪' : '📚'
    const scoreBg = results.percentage >= 80 ? 'from-green-400 to-green-600' : results.percentage >= 60 ? 'from-blue-400 to-blue-600' : results.percentage >= 40 ? 'from-yellow-400 to-yellow-600' : 'from-red-400 to-red-600'
    const dk = results.dunning_kruger
    const pct = results.percentage

    // ─── MODIFICATION — Diagnostic explicite par profil ───────────────────
    const profilMessages = {
      dunning_kruger_peak: {
        emoji: "⚠️", title: "Tu es au Pic de Dunning-Kruger",
        color: "bg-red-50 border-red-300", text: "text-red-700", bg: "bg-red-100",
        diagnosis: "Tu surestimes significativement tes connaissances.",
        detail: `Tu as obtenu ${pct}% mais tu te sentais très confiant. C'est le signe classique du pic de Dunning-Kruger : on ne sait pas encore qu'on ne sait pas. C'est une étape normale — la prise de conscience est le premier pas.`
      },
      impostor_syndrome: {
        emoji: "💪", title: "Tu souffres du Syndrome de l'Imposteur",
        color: "bg-blue-50 border-blue-300", text: "text-blue-700", bg: "bg-blue-100",
        diagnosis: "Tu sous-estimes tes vraies compétences.",
        detail: `Tu as obtenu ${pct}% mais tu ne te faisais pas confiance. Tu sais plus que tu ne le penses ! Le syndrome de l'imposteur te fait douter de tes propres acquis. Fais confiance à tes résultats.`
      },
      expert_calibrated: {
        emoji: "🎯", title: "Tu es un Expert Calibré",
        color: "bg-green-50 border-green-300", text: "text-green-700", bg: "bg-green-100",
        diagnosis: "Tu connais exactement ton niveau — profil idéal.",
        detail: `Tu as obtenu ${pct}% et tu t'es évalué avec précision. C'est le profil le plus rare et le plus précieux : expertise réelle et humilité réunies.`
      },
      slope_of_enlightenment: {
        emoji: "📈", title: "Tu es sur la Pente de l'Illumination",
        color: "bg-teal-50 border-teal-300", text: "text-teal-700", bg: "bg-teal-100",
        diagnosis: "Tu progresses et tu commences à bien te connaître.",
        detail: `Tu as obtenu ${pct}% avec une confiance bien calibrée. Tu sors de la vallée du désespoir et tu montes vers la maîtrise. Continue — tu es sur la bonne voie.`
      },
      valley_of_despair: {
        emoji: "😓", title: "Tu es dans la Vallée du Désespoir",
        color: "bg-orange-50 border-orange-300", text: "text-orange-700", bg: "bg-orange-100",
        diagnosis: "Tu réalises la complexité du sujet et tu te décourages.",
        detail: `Tu as obtenu ${pct}%. Tu sais maintenant que c'est plus difficile que tu ne pensais — c'est une étape normale et nécessaire. Tous les experts sont passés par là. La maîtrise arrive après cette vallée.`
      },
      beginner_calibrated: {
        emoji: "🌱", title: "Tu es un Débutant Calibré",
        color: "bg-yellow-50 border-yellow-300", text: "text-yellow-700", bg: "bg-yellow-100",
        diagnosis: "Tu sais ce que tu ne sais pas encore — c'est excellent.",
        detail: `Tu as obtenu ${pct}% et tu t'es évalué honnêtement. Reconnaître ses lacunes est la première qualité d'un bon apprenant. Tu construis sur des bases solides.`
      },
      conscious_incompetence: {
        emoji: "📚", title: "Tu es dans l'Incompétence Consciente",
        color: "bg-orange-50 border-orange-300", text: "text-orange-700", bg: "bg-orange-100",
        diagnosis: "Tu sais que tu as des lacunes — c'est déjà un grand pas.",
        detail: `Tu as obtenu ${pct}%. Être conscient de ce qu'on ne sait pas est la condition nécessaire pour apprendre efficacement. Tu évites le piège de la fausse confiance.`
      },
      expert_overconfident: {
        emoji: "⚠️", title: "Tu es un Expert légèrement Surconfiant",
        color: "bg-yellow-50 border-yellow-300", text: "text-yellow-700", bg: "bg-yellow-100",
        diagnosis: "Tu maîtrises très bien mais tu surestimes légèrement.",
        detail: `Tu as obtenu ${pct}% — c'est excellent. Attention à la légère surconfiance qui peut mener à des erreurs d'inattention. Reste vigilant sur les détails.`
      },
      expert_modest: {
        emoji: "🏅", title: "Tu es un Expert Humble",
        color: "bg-green-50 border-green-300", text: "text-green-700", bg: "bg-green-100",
        diagnosis: "Tu maîtrises parfaitement et tu restes humble.",
        detail: `Tu as obtenu ${pct}% avec une confiance mesurée. C'est le profil d'un expert accompli qui continue de progresser. Partage tes connaissances avec les autres.`
      },
    }

    const profilInfo = dk
      ? (profilMessages[dk.zone] || {
          emoji: "📊", title: dk.zone_label,
          color: "bg-gray-50 border-gray-300", text: "text-gray-700", bg: "bg-gray-100",
          diagnosis: dk.message, detail: dk.recommendation
        })
      : null

    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-100 to-blue-50">
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
            <h1 className="text-lg font-bold text-gray-800">📋 Tes Résultats</h1>
            <div className="flex gap-3">
              <button onClick={handleDownloadPDF} className="bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded-lg text-sm">📄 Télécharger PDF</button>
              <button onClick={() => { setReportEmail(userEmail); setShowEmailModal(true) }} className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg text-sm">📧 Envoyer par email</button>
              <button onClick={onBackToHome} className="bg-primary-600 text-white font-semibold py-2 px-4 rounded-lg text-sm">← Retour</button>
            </div>
          </div>
        </header>

        {showEmailModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl p-8 max-w-md w-full shadow-2xl">
              <h3 className="text-xl font-bold text-gray-900 mb-2">📧 Envoyer le rapport</h3>
              <p className="text-gray-500 text-sm mb-6">Le rapport PDF sera envoyé à cette adresse email.</p>
              <input type="email" value={reportEmail} onChange={(e) => setReportEmail(e.target.value)}
                placeholder="votre@email.com" className="w-full px-4 py-3 border border-gray-300 rounded-lg mb-4 text-gray-900" />
              {emailError && <p className="text-red-600 text-sm mb-4">❌ {emailError}</p>}
              {emailSent  && <p className="text-green-600 text-sm mb-4">✅ Rapport envoyé avec succès !</p>}
              <div className="flex gap-3">
                <button onClick={() => setShowEmailModal(false)} className="flex-1 bg-gray-100 text-gray-700 font-semibold py-3 rounded-lg">Annuler</button>
                <button onClick={handleSendEmail} disabled={emailSending} className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-lg disabled:opacity-50">
                  {emailSending ? '⏳ Envoi...' : '📧 Envoyer'}
                </button>
              </div>
            </div>
          </div>
        )}

        <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">

          {/* Score */}
          <div className={`bg-gradient-to-br ${scoreBg} rounded-3xl p-8 text-white text-center shadow-2xl`}>
            <div className="text-8xl mb-4">{scoreEmoji}</div>
            <div className="text-7xl font-black mb-2">{results.percentage}%</div>
            <div className="flex justify-center flex-wrap gap-3 mb-4">
              {results.question_results.map((qr, idx) => (
                <div key={idx} className={`w-12 h-12 rounded-full flex items-center justify-center text-xl font-bold border-2 border-white/40 ${
                  qr.user_answer === null ? 'bg-white/20' : qr.is_correct ? 'bg-white text-green-600' : 'bg-white/20'
                }`}>
                  {qr.user_answer === null ? '–' : qr.is_correct ? '✓' : '✗'}
                </div>
              ))}
            </div>
            <p className="text-white/80 text-lg">
              <strong>{results.score}</strong> bonne(s) réponse(s) sur <strong>{results.total_questions}</strong>
            </p>
          </div>

          {/* ─── DIAGNOSTIC DK — Version explicite ─── */}
          {dk && profilInfo && (
            <div className={`rounded-3xl p-6 shadow-lg border-2 ${profilInfo.color}`}>
              {/* En-tête */}
              <div className="flex items-center gap-4 mb-4">
                <span className="text-5xl">{profilInfo.emoji}</span>
                <div>
                  <p className="text-xs font-bold uppercase tracking-widest text-gray-400 mb-1">
                    Diagnostic Cognitif
                  </p>
                  <h2 className={`text-2xl font-bold ${profilInfo.text}`}>
                    {profilInfo.title}
                  </h2>
                </div>
              </div>

              {/* Boîte diagnostic */}
              <div className={`rounded-2xl p-4 mb-4 ${profilInfo.bg}`}>
                <p className={`font-bold text-base mb-2 ${profilInfo.text}`}>
                  {profilInfo.diagnosis}
                </p>
                <p className="text-gray-600 text-sm leading-relaxed">
                  {profilInfo.detail}
                </p>
              </div>

              {/* Recommandation */}
              <p className="text-gray-500 italic text-sm mb-3">
                💡 {dk.recommendation}
              </p>

              {/* Profil ML */}
              {dk.profil_ml && (
                <div className="inline-flex items-center gap-2 bg-white rounded-full px-4 py-2 shadow-sm">
                  <span className="text-sm text-gray-400">🤖 Profil ML :</span>
                  <span className={`font-bold text-sm ${profilInfo.text}`}>
                    {dk.profil_ml === 'overconfident' ? 'Surconfiant' :
                     dk.profil_ml === 'impostor'      ? 'Syndrome Imposteur' :
                     dk.profil_ml === 'calibrated'    ? 'Calibré' :
                     dk.profil_ml === 'conscious'     ? 'Conscient' : dk.profil_ml}
                  </span>
                  {dk.confidence_ml && (
                    <span className="text-xs text-gray-400">({Math.round(dk.confidence_ml * 100)}% certitude)</span>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Courbe DK */}
          {dk && <DunningKrugerChart dk={dk} />}

          {/* Confiance vs Score */}
          {dk && (
            <div className="bg-white rounded-3xl p-6 shadow-lg">
              <h2 className="text-xl font-bold text-gray-800 mb-4">🧠 Comparaison confiance / performance</h2>
              <div className="space-y-3">
                {[
                  { label: "💬 Confiance déclarée", value: dk.declared_confidence, color: "bg-blue-500", bg: "bg-blue-100" },
                  { label: "✅ Score réel", value: dk.actual_score, color: "bg-green-500", bg: "bg-green-100" },
                  ...(dk.observed_confidence != null ? [{ label: "📷 Confiance observée (visage)", value: dk.observed_confidence, color: "bg-purple-500", bg: "bg-purple-100" }] : [])
                ].map((item, i) => (
                  <div key={i}>
                    <div className="flex justify-between text-sm font-medium text-gray-700 mb-1">
                      <span>{item.label}</span>
                      <span className="font-bold">{item.value}%</span>
                    </div>
                    <div className={`w-full ${item.bg} rounded-full h-6 overflow-hidden`}>
                      <div className={`h-6 ${item.color} rounded-full flex items-center justify-end pr-2`} style={{ width: `${item.value}%` }}>
                        <span className="text-white text-xs font-bold">{item.value}%</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Bouton analyse notions */}
          {!notions && !notionsLoading && (
            <div className="bg-white rounded-3xl p-6 shadow-lg text-center border-2 border-dashed border-primary-200">
              <p className="text-2xl mb-3">🤖</p>
              <h2 className="text-xl font-bold text-gray-800 mb-2">Analyse des notions</h2>
              <p className="text-gray-500 text-sm mb-5">
                L'IA va analyser vos réponses et identifier les notions à réviser
                ainsi que les compétences que vous sous-estimez.
                <br />
                <span className="text-orange-500 font-medium">Cette analyse prend 1-2 minutes.</span>
              </p>
              <button onClick={fetchNotions} className="bg-primary-600 hover:bg-primary-700 text-white font-bold py-3 px-8 rounded-xl transition-all">
                🔍 Analyser mes notions via IA
              </button>
            </div>
          )}

          {notionsLoading && (
            <div className="bg-white rounded-3xl p-6 shadow-lg text-center">
              <div className="w-10 h-10 border-4 border-primary-300 border-t-primary-600 rounded-full animate-spin mx-auto mb-4"></div>
              <p className="text-gray-700 font-medium">🤖 Analyse en cours via Ollama...</p>
              <p className="text-gray-400 text-sm mt-1">Identification des notions à réviser</p>
            </div>
          )}

          {notions && notions.notions_to_revise && notions.notions_to_revise.length > 0 && (
            <div className="bg-white rounded-3xl p-6 shadow-lg border-l-4 border-red-400">
              <h2 className="text-xl font-bold text-gray-800 mb-2">📚 Notions à Réviser</h2>
              <p className="text-gray-500 text-sm mb-4">Ces concepts ont été identifiés à partir de vos réponses incorrectes.</p>
              <div className="space-y-3">
                {notions.notions_to_revise.map((n, idx) => (
                  <div key={idx} className="bg-red-50 border border-red-200 rounded-2xl p-4">
                    <div className="flex items-start gap-3">
                      <span className="bg-red-500 text-white rounded-full w-7 h-7 flex items-center justify-center text-sm font-bold flex-shrink-0">{idx + 1}</span>
                      <div>
                        <p className="font-bold text-red-800 text-sm">{n.notion}</p>
                        <p className="text-gray-500 text-xs mt-1">{n.question}</p>
                        <p className="text-gray-400 text-xs mt-1 italic">💡 {n.explanation}</p>
                        <div className="flex gap-3 mt-2">
                          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full">Confiance : {n.declared_confidence}%</span>
                          <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded-full">Visage : {n.confidence_observed}%</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {notions && notions.mastered_notions && notions.mastered_notions.length > 0 && (
            <div className="bg-white rounded-3xl p-6 shadow-lg border-l-4 border-green-400">
              <h2 className="text-xl font-bold text-gray-800 mb-2">💪 Compétences Maîtrisées mais Sous-Estimées</h2>
              <p className="text-gray-500 text-sm mb-4">Tu maîtrises ces notions sans le savoir. Fais confiance à tes acquis !</p>
              <div className="space-y-3">
                {notions.mastered_notions.map((n, idx) => (
                  <div key={idx} className="bg-green-50 border border-green-200 rounded-2xl p-4">
                    <div className="flex items-start gap-3">
                      <span className="bg-green-500 text-white rounded-full w-7 h-7 flex items-center justify-center text-sm font-bold flex-shrink-0">✓</span>
                      <div>
                        <p className="font-bold text-green-800 text-sm">{n.notion}</p>
                        <p className="text-gray-500 text-xs mt-1">{n.question}</p>
                        <div className="flex gap-3 mt-2">
                          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full">Confiance déclarée : {n.declared_confidence}%</span>
                          <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">✅ Réussi !</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {notions && notions.personalized_message && (
            <div className="bg-gradient-to-br from-primary-50 to-teal-50 rounded-3xl p-6 shadow-lg border border-teal-200">
              <h2 className="text-xl font-bold text-primary-800 mb-3">🎯 Votre Message Personnalisé</h2>
              <p className="text-gray-700 whitespace-pre-line leading-relaxed">{notions.personalized_message}</p>
            </div>
          )}

          {/* Recommandations */}
          <div className="bg-white rounded-3xl p-6 shadow-lg">
            <h2 className="text-xl font-bold text-gray-800 mb-4">💡 Conseils</h2>
            <div className="space-y-3">
              {results.recommendations.map((rec, idx) => {
                const tipEmojis = ['🚀', '📖', '✏️', '🧩', '🏅']
                return (
                  <div key={idx} className="flex items-center gap-3 bg-primary-50 rounded-2xl px-4 py-3 border border-primary-100">
                    <span className="text-2xl">{tipEmojis[idx % tipEmojis.length]}</span>
                    <p className="text-gray-700 font-medium">{rec}</p>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Détail questions */}
          <div className="bg-white rounded-3xl p-6 shadow-lg">
            <h2 className="text-xl font-bold text-gray-800 mb-5">🔍 Revoir les questions</h2>
            <div className="space-y-4">
              {results.question_results.map((qr, idx) => {
                const wasAnswered = qr.user_answer !== null && qr.user_answer !== undefined
                const correct = wasAnswered && qr.is_correct
                return (
                  <div key={idx} className={`rounded-2xl border-2 p-5 ${!wasAnswered ? 'border-gray-200 bg-gray-50' : correct ? 'border-green-300 bg-green-50' : 'border-red-200 bg-red-50'}`}>
                    <div className="flex items-center gap-3 mb-3">
                      <span className="text-3xl">{!wasAnswered ? '⬜' : correct ? '✅' : '❌'}</span>
                      <div>
                        <span className="text-xs font-bold uppercase text-gray-400">Question {idx + 1}</span>
                        <p className="font-semibold text-gray-900 text-sm">{qr.question}</p>
                      </div>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-3">
                      {qr.options.map((opt, optIdx) => {
                        const isCorrect  = optIdx === qr.correct_answer
                        const isSelected = wasAnswered && optIdx === qr.user_answer
                        return (
                          <div key={optIdx} className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm ${isCorrect ? 'bg-green-200 border border-green-400 font-semibold text-green-900' : isSelected && !isCorrect ? 'bg-red-200 border border-red-400 text-red-800' : 'bg-white border border-gray-200 text-gray-700'}`}>
                            <span className="font-bold text-gray-400">{String.fromCharCode(65 + optIdx)})</span>
                            <span>{opt}</span>
                            {isCorrect && <span className="ml-auto">✅</span>}
                            {isSelected && !isCorrect && <span className="ml-auto">❌</span>}
                          </div>
                        )
                      })}
                    </div>
                    <div className="bg-white rounded-xl px-4 py-3 border-l-4 border-primary-400">
                      <p className="text-xs font-bold text-primary-700 mb-1">💡 Explication</p>
                      <p className="text-sm text-gray-600">{qr.explanation}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Boutons bas */}
          <div className="flex flex-col sm:flex-row gap-3 pb-8">
            <button onClick={handleDownloadPDF} className="flex-1 bg-green-600 hover:bg-green-700 text-white font-bold py-4 rounded-2xl shadow-lg text-lg flex items-center justify-center gap-2">
              📄 Télécharger mon rapport PDF
            </button>
            <button onClick={() => { setReportEmail(userEmail); setShowEmailModal(true) }} className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 rounded-2xl shadow-lg text-lg flex items-center justify-center gap-2">
              📧 Recevoir par email
            </button>
            <button onClick={onBackToHome} className="bg-gradient-to-r from-primary-600 to-primary-700 text-white font-bold py-4 px-8 rounded-2xl shadow-lg text-lg">
              🏠 Accueil
            </button>
          </div>

        </main>
      </div>
    )
  }

  // ─── STEPS 1, 2, 3 ─────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-primary-100">
      <header className="bg-white shadow-sm border-b border-primary-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center space-x-4">
            <button onClick={onBackToHome} className="text-primary-600 flex items-center space-x-2">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              <span className="font-medium">Retour</span>
            </button>
            <div className="h-6 w-px bg-primary-200"></div>
            <div>
              <h1 className="text-3xl font-bold text-primary-800">Projet SIMCO</h1>
              <p className="text-sm text-primary-600 mt-1">Système Intelligent Multimodal d'Évaluation Cognitive</p>
            </div>
          </div>
        </div>
      </header>

      {currentStep < 4 && (
        <div className="bg-white border-b border-primary-200">
          <div className="max-w-4xl mx-auto px-4 py-6">
            <div className="flex items-center justify-between">
              {[1, 2, 3].map((step) => (
                <div key={step} className="flex items-center flex-1">
                  <div className="flex items-center">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold ${currentStep >= step ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-500'}`}>
                      {currentStep > step ? '✓' : step}
                    </div>
                    <span className={`ml-3 font-medium ${currentStep >= step ? 'text-primary-700' : 'text-gray-500'}`}>
                      {step === 1 && 'Informations'}{step === 2 && 'Préférences'}{step === 3 && 'Instructions'}
                    </span>
                  </div>
                  {step < 3 && <div className={`flex-1 h-1 mx-4 rounded ${currentStep > step ? 'bg-primary-600' : 'bg-gray-200'}`}></div>}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <main className="max-w-4xl mx-auto px-4 py-12">
        {currentStep === 1 && (
          <div className="bg-white rounded-2xl shadow-xl border border-primary-200 p-8 md:p-12">
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold text-gray-900 mb-2">Bienvenue !</h2>
              <p className="text-gray-600">Informations de base pour personnaliser votre expérience</p>
            </div>
            <form onSubmit={handleUserInfoSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Nom complet *</label>
                <input type="text" value={userName} onChange={(e) => setUserName(e.target.value)} placeholder="Ex: Jean Dupont" required className="w-full px-4 py-3 border border-primary-300 rounded-lg bg-white text-gray-900" />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Âge *</label>
                  <input type="number" value={userAge} onChange={(e) => setUserAge(e.target.value)} placeholder="Ex: 16" min="10" max="100" required className="w-full px-4 py-3 border border-primary-300 rounded-lg bg-white text-gray-900" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Niveau académique *</label>
                  <select value={userAcademicLevel} onChange={(e) => setUserAcademicLevel(e.target.value)} className="w-full px-4 py-3 border border-primary-300 rounded-lg bg-white text-gray-900">
                    <option value="collège">Collège</option>
                    <option value="lycée">Lycée</option>
                    <option value="université">Université</option>
                    <option value="professionnel">Professionnel</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Email — pour recevoir votre rapport</label>
                <input type="email" value={userEmail} onChange={(e) => setUserEmail(e.target.value)} placeholder="Ex: jean.dupont@email.com" className="w-full px-4 py-3 border border-primary-300 rounded-lg bg-white text-gray-900" />
              </div>
              <button type="submit" className="w-full bg-gradient-to-r from-primary-600 to-primary-700 text-white font-semibold py-4 rounded-lg shadow-lg">Continuer →</button>
            </form>
          </div>
        )}

        {currentStep === 2 && (
          <div className="bg-white rounded-2xl shadow-xl border border-primary-200 p-8 md:p-12">
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold text-gray-900 mb-2">Préférences d'évaluation</h2>
            </div>
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Domaine d'étude *</label>
                <select value={subject} onChange={(e) => setSubject(e.target.value)} className="w-full px-4 py-3 border border-primary-300 rounded-lg bg-white text-gray-900">
                  <option value="mathématiques">Mathématiques</option>
                  <option value="physique">Physique</option>
                  <option value="chimie">Chimie</option>
                  <option value="biologie">Biologie</option>
                  <option value="histoire">Histoire</option>
                  <option value="géographie">Géographie</option>
                  <option value="français">Français</option>
                  <option value="anglais">Anglais</option>
                  <option value="informatique">Informatique</option>
                  <option value="philosophie">Philosophie</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Niveau de difficulté *</label>
                <select value={level} onChange={(e) => setLevel(e.target.value)} className="w-full px-4 py-3 border border-primary-300 rounded-lg bg-white text-gray-900">
                  <option value="collège">Collège (débutant)</option>
                  <option value="lycée">Lycée (intermédiaire)</option>
                  <option value="université">Université (avancé)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Informations complémentaires (optionnel)</label>
                <textarea value={userInfo} onChange={(e) => setUserInfo(e.target.value)} rows={3} className="w-full px-4 py-3 border border-primary-300 rounded-lg resize-none bg-white text-gray-900" />
              </div>
              <div className="flex space-x-4">
                <button onClick={() => setCurrentStep(1)} className="flex-1 bg-white text-gray-700 font-semibold py-4 rounded-lg border-2 border-gray-300">Retour</button>
                <button onClick={handlePreferencesSubmit} className="flex-1 bg-gradient-to-r from-primary-600 to-primary-700 text-white font-semibold py-4 rounded-lg shadow-lg">Continuer →</button>
              </div>
            </div>
          </div>
        )}

        {currentStep === 3 && (
          <div className="bg-white rounded-2xl shadow-xl border border-primary-200 p-8 md:p-12">
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold text-gray-900 mb-2">Instructions importantes</h2>
            </div>
            <div className="bg-amber-50 border-l-4 border-amber-500 p-6 rounded-r-lg mb-8">
              <p className="text-amber-800 font-medium">⚠️ Une fois commencé, vous ne pouvez plus arrêter le test.</p>
            </div>
            <div className="space-y-4 mb-8">
              {[
                { icon: '⏱️', title: 'Durée', desc: '20 minutes pour répondre aux questions.' },
                { icon: '🖥️', title: 'Plein écran', desc: 'Le test se déroule en mode plein écran.' },
                { icon: '📷', title: 'Caméra', desc: 'Analyse vos expressions pour mesurer la confiance réelle.' },
                { icon: '📊', title: 'Rapport', desc: 'Un rapport PDF personnalisé sera généré à la fin.' },
              ].map((item, i) => (
                <div key={i} className="flex items-start space-x-4">
                  <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center text-xl">{item.icon}</div>
                  <div>
                    <h4 className="font-semibold text-gray-900">{item.title}</h4>
                    <p className="text-gray-600">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="flex space-x-4">
              <button onClick={() => setCurrentStep(2)} className="flex-1 bg-white text-gray-700 font-semibold py-4 rounded-lg border-2 border-gray-300">Retour</button>
              <button onClick={startTest} className="flex-1 bg-gradient-to-r from-primary-600 to-primary-700 text-white font-semibold py-4 rounded-lg shadow-lg">Commencer le test</button>
            </div>
          </div>
        )}
      </main>

      <footer className="bg-white border-t border-primary-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <p className="text-center text-sm text-primary-600">© 2026 Projet SIMCO</p>
        </div>
      </footer>
    </div>
  )
}

export default QuizPage