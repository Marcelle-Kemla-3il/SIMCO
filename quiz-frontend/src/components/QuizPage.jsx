import { useState, useCallback, useEffect, useRef } from 'react'

const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL || 'http://127.0.0.1:8080'

const QuizPage = ({ subject: propSubject, level: propLevel }) => {
  // Multi-step state
  const [currentStep, setCurrentStep] = useState(1)
  
  // User information
  const [userName, setUserName] = useState('')
  const [userEmail, setUserEmail] = useState('')
  
  // Quiz settings
  const [subject, setSubject] = useState(propSubject || 'mathématiques')
  const [level, setLevel] = useState(propLevel || 'lycée')
  const [classLevel, setClassLevel] = useState('')
  const [sector, setSector] = useState('informatique_data')
  const [difficulty, setDifficulty] = useState('medium')
  
  // Quiz state
  const [questions, setQuestions] = useState([])
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [question, setQuestion] = useState(null)
  const [loading, setLoading] = useState(false)
  const [selectedOption, setSelectedOption] = useState(null)
  const [finalDeclaredConfidence, setFinalDeclaredConfidence] = useState(50)
  const [timeRemaining, setTimeRemaining] = useState(10)
  const [autoSubmittedKey, setAutoSubmittedKey] = useState(null)
  const [cameraEnabled, setCameraEnabled] = useState(false)
  const [cameraError, setCameraError] = useState(null)
  const [facesCount, setFacesCount] = useState(null)
  const [dominantEmotion, setDominantEmotion] = useState(null)
  const [videoEl, setVideoEl] = useState(null)
  const [streamRef, setStreamRef] = useState(null)
  const [sessionId, setSessionId] = useState(null)
  const [results, setResults] = useState(null)
  const [answers, setAnswers] = useState([])
  const [generationError, setGenerationError] = useState(null)
  const [generationWarning, setGenerationWarning] = useState(null)
  const [globalConfidenceSubmitted, setGlobalConfidenceSubmitted] = useState(false)
  
  // UI state
  const [showReadyScreen, setShowReadyScreen] = useState(false)
  const isMountedRef = useRef(true)
  const allowCameraStateUpdatesRef = useRef(false)
  const questionStartMsRef = useRef(null)
  const noFaceSinceMsRef = useRef(null)

  const WarningBanner = generationWarning ? (
    <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-amber-900">
      {generationWarning}
    </div>
  ) : null

  const startCamera = useCallback(async () => {
    setCameraError(null)
    try {
      if (!navigator?.mediaDevices?.getUserMedia) {
        throw new Error('CAMERA_UNSUPPORTED')
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'user',
          width: { ideal: 640 },
          height: { ideal: 480 }
        },
        audio: false
      })

      setStreamRef(stream)
      setCameraEnabled(true)
      return true
    } catch (e) {
      setCameraEnabled(false)
      const name = e?.name || ''
      const msg =
        name === 'NotAllowedError' || name === 'PermissionDeniedError'
          ? "Veuillez autoriser la caméra pour démarrer le quiz."
          : "Impossible d'activer la caméra. Vérifiez votre navigateur et réessayez."
      setCameraError(msg)
      return false
    }
  }, [])

  const normalizeOptionId = useCallback((rawId) => {
    const s = String(rawId ?? '').trim().toUpperCase()
    if (s === 'UN' || s === '1') return 'A'
    if (s === 'DEUX' || s === '2') return 'B'
    if (s === 'TROIS' || s === '3') return 'C'
    if (s === 'QUATRE' || s === '4') return 'D'
    if (['A', 'B', 'C', 'D'].includes(s)) return s
    return s
  }, [])

  const getDisplayOptionId = useCallback((option, idx) => {
    return ['A', 'B', 'C', 'D'][idx] || normalizeOptionId(option?.id)
  }, [normalizeOptionId])

  const formatTime = useCallback((seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }, [])

  const showQuizResults = useCallback(async () => {
    try {
      const [sessionResp, reportResp] = await Promise.all([
        fetch(`${API_BASE_URL}/api/v1/quiz/sessions/${sessionId}`),
        fetch(`${API_BASE_URL}/api/v1/quiz/sessions/${sessionId}/report`)
      ])

      const sessionData = sessionResp.ok ? await sessionResp.json() : null
      const reportData = reportResp.ok ? await reportResp.json() : null

      const correctAnswersCount = answers.filter(ans => ans.isCorrect).length
      const totalQuestionsAnswered = answers.length
      const calculatedPercentage = totalQuestionsAnswered > 0 ? Math.round((correctAnswersCount / totalQuestionsAnswered) * 100) : 0

      const declaredGlobal = reportData?.confidence?.declared_global
      const observedAvg = reportData?.confidence?.observed_avg
      const biasFlags = reportData?.biases?.flags
      const biasNotes = reportData?.biases?.notes

      const results = {
        percentage: typeof reportData?.results?.score_percentage === 'number'
          ? Math.round(reportData.results.score_percentage)
          : calculatedPercentage,
        score: correctAnswersCount * 10,
        total_questions: sessionData?.total_questions || reportData?.quiz?.total_questions || totalQuestionsAnswered,
        answered_count: reportData?.results?.answered || totalQuestionsAnswered,
        declared_confidence: typeof declaredGlobal === 'number' ? declaredGlobal : 0.5,
        observed_confidence: typeof observedAvg === 'number' ? observedAvg : 0.5,
        bias_flags: {
          dunning_kruger: Boolean(biasFlags?.dunning_kruger),
          impostor: Boolean(biasFlags?.impostor)
        },
        bias_notes: Array.isArray(biasNotes) ? biasNotes : [],
        question_results: answers.map(ans => ({
          user_answer: ans.selectedOption,
          is_correct: ans.isCorrect
        }))
      }

      setResults(results)
      setCurrentStep(6)
    } catch (error) {
      console.error('Error showing results:', error)
      // Fallback to basic results
      const correctAnswersCount = answers.filter(ans => ans.isCorrect).length
      const totalQuestionsAnswered = answers.length
      const calculatedPercentage = totalQuestionsAnswered > 0 ? Math.round((correctAnswersCount / totalQuestionsAnswered) * 100) : 0
      
      setResults({
        percentage: calculatedPercentage,
        score: correctAnswersCount * 10,
        total_questions: totalQuestionsAnswered,
        answered_count: totalQuestionsAnswered,
        declared_confidence: 0.5,
        observed_confidence: 0.5,
        bias_flags: { dunning_kruger: false, impostor: false },
        bias_notes: []
      })
      setCurrentStep(6)
    }
  }, [answers, sessionId])

  useEffect(() => {
    if (currentStep === 5) return
    setAutoSubmittedKey(null)
  }, [currentStep])

  useEffect(() => {
    return () => {
      try {
        const s = streamRef
        if (s && typeof s.getTracks === 'function') {
          s.getTracks().forEach((t) => t.stop())
        }
      } catch {
        // ignore
      }
    }
  }, [streamRef])

  useEffect(() => {
    if (level !== 'professionnel') {
      setSector('informatique_data')
    }
  }, [level])

  useEffect(() => {
    if (level === 'professionnel') {
      setSubject('informatique')
    }
  }, [level])

  const captureAndAnalyzeFrame = useCallback(async () => {
    if (!videoEl) return
    if (!cameraEnabled) return
    if (!videoEl.videoWidth || !videoEl.videoHeight) return
    if (!sessionId) return

    try {
      const canvas = document.createElement('canvas')
      canvas.width = videoEl.videoWidth
      canvas.height = videoEl.videoHeight
      const ctx = canvas.getContext('2d')
      ctx.drawImage(videoEl, 0, 0)

      const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.7))
      if (!blob) return

      const form = new FormData()
      form.append('file', blob, 'frame.jpg')

      const res = await fetch(`${API_BASE_URL}/api/v1/cv/analyze-frame`, {
        method: 'POST',
        body: form
      })

      if (!res.ok) {
        return
      }

      const data = await res.json()
      if (!isMountedRef.current) return
      const nextFacesCount = typeof data.faces_count === 'number' ? data.faces_count : null
      const nextDominantEmotion = typeof data.dominant_emotion === 'string' ? data.dominant_emotion : null

      if (typeof nextFacesCount === 'number' && nextFacesCount <= 0) {
        if (noFaceSinceMsRef.current == null) {
          noFaceSinceMsRef.current = performance.now()
        } else {
          const elapsed = performance.now() - noFaceSinceMsRef.current
          if (elapsed >= 5000) {
            alert("Visage non détecté depuis plus de 5 secondes.\nRetour à l'accueil du quiz.")
            noFaceSinceMsRef.current = null
            setCurrentStep(1)
            setSessionId(null)
            setQuestions([])
            setQuestion(null)
            setSelectedOption(null)
            setFacesCount(null)
            setDominantEmotion(null)
            return
          }
        }
      } else {
        noFaceSinceMsRef.current = null
      }

      setFacesCount(nextFacesCount)
      setDominantEmotion(nextDominantEmotion)

      const nextEmotions = (data && typeof data === 'object' && data.emotions && typeof data.emotions === 'object')
        ? data.emotions
        : undefined

      try {
        const params = new URLSearchParams()
        params.set('session_id', String(sessionId))
        params.set('question_index', String(currentQuestionIndex))
        if (typeof nextFacesCount === 'number') params.set('faces_count', String(nextFacesCount))
        if (nextDominantEmotion) params.set('dominant_emotion', nextDominantEmotion)

        await fetch(`${API_BASE_URL}/api/v1/cv/event?${params.toString()}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            emotions: nextEmotions
          })
        })
      } catch (e) {
        // non-blocking
      }
    } catch {
      // ignore
    }
  }, [cameraEnabled, currentQuestionIndex, sessionId, videoEl])

  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  useEffect(() => {
    allowCameraStateUpdatesRef.current = currentStep === 5 && !showReadyScreen
  }, [currentStep, showReadyScreen])

  useEffect(() => {
    // Pre-enable camera on the ready screen BEFORE quiz starts.
    if (currentStep !== 5) return
    if (!showReadyScreen) return
    if (cameraEnabled) return
    startCamera()
  }, [cameraEnabled, currentStep, showReadyScreen, startCamera])

  useEffect(() => {
    if (!streamRef || !videoEl) return
    videoEl.srcObject = streamRef
    const play = async () => {
      try {
        await videoEl.play()
      } catch {
        // ignore
      }
    }
    play()
  }, [streamRef, videoEl])

  useEffect(() => {
    if (!cameraEnabled) return
    if ((currentStep !== 5 && currentStep !== 6) || showReadyScreen) return
    const id = window.setInterval(() => {
      captureAndAnalyzeFrame()
    }, 2000)
    return () => window.clearInterval(id)
  }, [cameraEnabled, captureAndAnalyzeFrame, currentStep, showReadyScreen])

  useEffect(() => {
    if (currentStep === 5 || currentStep === 6) return
    if (!streamRef) return
    streamRef.getTracks().forEach(t => t.stop())
    setStreamRef(null)
    setCameraEnabled(false)
    setFacesCount(null)
    setDominantEmotion(null)
  }, [currentStep, streamRef])

  const submitAnswerInternal = useCallback(async (answerOverride) => {
    const answerToSend = answerOverride ?? selectedOption
    if (answerToSend === null) {
      return
    }

    if (!sessionId) {
      return
    }

    setLoading(true)

    try {
      const startedAt = typeof questionStartMsRef.current === 'number'
        ? questionStartMsRef.current
        : null
      const responseTimeMs = startedAt !== null
        ? Math.max(0, Math.round(performance.now() - startedAt))
        : 0

      const response = await fetch(`${API_BASE_URL}/api/v1/quiz/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          question_index: currentQuestionIndex,
          selected_answer: normalizeOptionId(answerToSend),
          // Confiance uniquement globale (fin de quiz)
          confidence_level: 0.5,
          response_time_ms: responseTimeMs
        })
      })

      const data = await response.json()

      setAnswers((prev) => ([...prev, {
        questionIndex: currentQuestionIndex,
        selectedOption: normalizeOptionId(answerToSend),
        confidence: null,
        isCorrect: data.is_correct
      }]))

      const isLast = currentQuestionIndex >= questions.length - 1

      if (isLast) {
        setCurrentStep(6)
        return
      }

      setTimeout(() => {
        setCurrentQuestionIndex((prev) => prev + 1)
        setSelectedOption(null)
        setTimeRemaining(10)
      }, 100)
    } catch (error) {
      console.error('Error submitting answer:', error)
      alert('Erreur lors de la soumission. Veuillez réessayer.')
    } finally {
      setLoading(false)
    }
  }, [currentQuestionIndex, normalizeOptionId, questions.length, selectedOption, sessionId])

  const submitFinalDeclaredConfidence = useCallback(async () => {
    if (!sessionId) return
    try {
      await fetch(`${API_BASE_URL}/api/v1/quiz/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          question_index: -1,
          selected_answer: '_',
          confidence_level: Math.min(1, Math.max(0, Number(finalDeclaredConfidence) / 100)),
          response_time_ms: 0
        })
      })
      setGlobalConfidenceSubmitted(true)
    } catch (e) {
      // non-blocking
    }
  }, [finalDeclaredConfidence, sessionId])

  const confirmGlobalConfidence = useCallback(async () => {
    await submitFinalDeclaredConfidence()
    await showQuizResults()
  }, [showQuizResults, submitFinalDeclaredConfidence])

  const submitAnswer = async () => {
    if (selectedOption === null) {
      alert('Veuillez sélectionner une réponse avant de soumettre.')
      return
    }

    await submitAnswerInternal(selectedOption)
  }

  useEffect(() => {
    if ((currentStep !== 5 && currentStep !== 6) || showReadyScreen) return
    if (!questions?.length) return

    setQuestion(questions[currentQuestionIndex] || null)
    setAutoSubmittedKey(`${sessionId ?? 's'}-${currentQuestionIndex}`)
    questionStartMsRef.current = performance.now()
  }, [currentQuestionIndex, currentStep, questions, sessionId, showReadyScreen])

  useEffect(() => {
    if (currentStep !== 5 || showReadyScreen) return
    if (!questions?.length) return
    if (!question) return

    setTimeRemaining(10)
    const intervalId = window.setInterval(() => {
      setTimeRemaining((prev) => Math.max(0, prev - 1))
    }, 1000)

    return () => window.clearInterval(intervalId)
  }, [currentStep, question, questions, showReadyScreen])

  useEffect(() => {
    if (currentStep !== 5 || showReadyScreen) return
    if (timeRemaining > 0) return
    if (!question) return
    if (loading) return

    const key = `${sessionId ?? 's'}-${currentQuestionIndex}`
    if (autoSubmittedKey !== key) {
      return
    }

    setAutoSubmittedKey(null)

    const fallbackAnswer = 'A'
    submitAnswerInternal(fallbackAnswer)
  }, [autoSubmittedKey, currentQuestionIndex, currentStep, loading, question, sessionId, showReadyScreen, submitAnswerInternal, timeRemaining])

  const generateQuestions = async () => {
    setLoading(true)
    setGenerationError(null)
    setGenerationWarning(null)
    setShowReadyScreen(false)
    setCurrentQuestionIndex(0)
    setCurrentStep(4)
    let timeoutId = null
    
    try {
      const controller = new AbortController()
      timeoutId = setTimeout(() => controller.abort(), 180000)

      const requestBody = {
        subject: subject,
        level: level,
        difficulty: difficulty,
        class_level: classLevel,
        force_refresh: true,
        num_questions: 20
      }
      
      if (level === 'professionnel') {
        requestBody.sector = sector
      }
      
      const response = await fetch(`${API_BASE_URL}/api/v1/quiz/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
        signal: controller.signal
      })

      clearTimeout(timeoutId)
      
      if (!response.ok) {
        let backendMsg = ''
        try {
          const contentType = response.headers.get('content-type') || ''
          if (contentType.includes('application/json')) {
            const errData = await response.json()
            backendMsg = String(errData?.detail || errData?.message || '')
          } else {
            backendMsg = String(await response.text())
          }
        } catch (_) {
          backendMsg = ''
        }
        throw new Error(backendMsg || `Failed to generate quiz (HTTP ${response.status})`)
      }
      
      const data = await response.json()
      const quiz = Array.isArray(data) ? data[0] : data
      
      if (!quiz) {
        throw new Error('No quiz data received')
      }
      
      // Create session
      const sessionController = new AbortController()
      const sessionTimeoutId = setTimeout(() => sessionController.abort(), 45000)

      const sessionResponse = await fetch(`${API_BASE_URL}/api/v1/quiz/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          quiz_id: quiz.id,
          student_id: userName,
          user_name: userName,
          user_email: userEmail,
          subject,
          level,
          class_level: classLevel
        }),
        signal: sessionController.signal
      })

      clearTimeout(sessionTimeoutId)
      
      if (!sessionResponse.ok) {
        throw new Error('Failed to create session')
      }
      
      const sessionData = await sessionResponse.json()
      
      const totalQuestions = Array.isArray(quiz?.questions) ? quiz.questions.length : 0
      if (totalQuestions < 10) {
        throw new Error('QUIZ_TOO_SHORT')
      }
      if (totalQuestions < 20) {
        setGenerationWarning(`Le backend a généré ${totalQuestions} questions sur 20. Le quiz démarre en mode best-effort.`)
      }

      // Format questions with hardcoded IDs
      const formattedQuestions = quiz.questions.map((q, idx) => {
        const options = Array.isArray(q.choices)
          ? q.choices.map((opt, optionIdx) => ({
              id: ['A', 'B', 'C', 'D'][optionIdx],
              rawId: ['A', 'B', 'C', 'D'][optionIdx],
              text: opt
            }))
          : Object.keys(q.choices).map((key, optionIdx) => ({
              id: ['A', 'B', 'C', 'D'][optionIdx],
              rawId: key,
              text: q.choices[key]
            }))
        
        return {
          id: idx + 1,
          question: q.question,
          options: options
        }
      })
      
      setQuestions(formattedQuestions)
      setQuestion(formattedQuestions[0])
      setSessionId(sessionData.id)
      setShowReadyScreen(true)
      setCurrentStep(5)
      setTimeRemaining(10)
      
    } catch (error) {
      console.error('Error generating quiz:', error)
      const backendDetail = typeof error === 'object' && error && String(error?.message || '')
      const message = error?.name === 'AbortError'
        ? 'La génération prend trop de temps. Vérifiez que le backend est démarré puis réessayez.'
        : (String(error?.message || '').includes('QUIZ_TOO_SHORT')
          ? 'Le backend a généré moins de 10 questions. Réessayez (force refresh) ou changez matière/niveau.'
          : (String(error?.message || '').startsWith('Erreur lors de la génération du quiz:')
            ? String(error?.message)
            : 'Erreur lors de la génération du quiz. Veuillez réessayez.'))

      setGenerationError(message)
      setCurrentStep(4)
    } finally {
      try {
        // Safety: ensure we never leave a pending abort timer
        // if an exception happened before clearTimeout.
        if (timeoutId) {
          clearTimeout(timeoutId)
        }
      } catch (_) {}
      setLoading(false)
    }
  }

  const cancelGeneration = () => {
    setLoading(false)
    setGenerationError(null)
    setCurrentStep(2)
  }

  const startQuiz = async () => {
    const ok = await startCamera()
    if (!ok) {
      return
    }
    setShowReadyScreen(false)
    setCurrentStep(5)
    setTimeRemaining(10) // Reset timer on quiz start
  }

  const downloadReport = () => {
    if (!sessionId) {
      alert('Session inconnue, impossible de générer le PDF.')
      return
    }

    const url = `${API_BASE_URL}/api/v1/quiz/sessions/${sessionId}/report.pdf`
    window.location.assign(url)
  }

  const sendEmailReport = async () => {
    if (!userEmail) {
      alert('Veuillez entrer votre adresse email au début du quiz');
      return;
    }
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/quiz/send-email-report/${sessionId}?email=${userEmail}`, {
        method: 'POST'
      });
      
      const data = await response.json();
      
      if (data.success) {
        alert('✅ Rapport envoyé par email !');
      } else {
        alert(`❌ Erreur: ${data.message}`);
      }
    } catch (error) {
      console.error('Error sending email report:', error);
      alert('❌ Erreur lors de l\'envoi de l\'email');
    }
  }

  // Step 1: User Info
  if (currentStep === 1) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-xl p-8 max-w-md w-full">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Informations de l'étudiant</h2>
          <form onSubmit={(e) => { e.preventDefault(); setCurrentStep(2); }}>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Nom/ID étudiant <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={userName}
                  onChange={(e) => setUserName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  placeholder="Entrez votre nom ou ID"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email <span className="text-red-500">*</span>
                </label>
                <input
                  type="email"
                  value={userEmail}
                  onChange={(e) => setUserEmail(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  placeholder="Entrez votre email"
                  required
                />
              </div>
            </div>
            <button
              type="submit"
              className="w-full bg-primary-600 hover:bg-primary-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors mt-6"
            >
              Suivant
            </button>
          </form>
        </div>
      </div>
    )
  }

  // Step 2: Subject Selection
  if (currentStep === 2) {
    const levelOptions = level === 'lycée'
      ? [
          { value: '', label: 'Sélectionner une classe' },
          { value: 'seconde', label: 'Seconde' },
          { value: 'premiere', label: 'Première' },
          { value: 'terminale', label: 'Terminale' }
        ]
      : level === 'universite'
        ? [
            { value: '', label: 'Sélectionner une année' },
            { value: 'L1', label: 'Licence 1 (L1)' },
            { value: 'L2', label: 'Licence 2 (L2)' },
            { value: 'L3', label: 'Licence 3 (L3)' },
            { value: 'M1', label: 'Master 1 (M1)' },
            { value: 'M2', label: 'Master 2 (M2)' }
          ]
        : [
            { value: '', label: 'Sélectionner un niveau' },
            { value: 'debutant', label: 'Débutant' },
            { value: 'intermediaire', label: 'Intermédiaire' },
            { value: 'avance', label: 'Avancé' }
          ]

    return (
      <div className="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-xl p-8 max-w-md w-full">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Choisissez votre domaine d'étude</h2>
          <div className="space-y-4">
            {level === 'professionnel' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Secteur professionnel <span className="text-red-500">*</span>
                </label>
                <select
                  value={sector}
                  onChange={(e) => setSector(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                >
                  <option value="informatique_data">Informatique / Data</option>
                  <option value="business_finance">Business / Finance</option>
                  <option value="sante">Santé</option>
                </select>
              </div>
            )}

            {level !== 'professionnel' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Domaine d'étude <span className="text-red-500">*</span>
                </label>
                <select
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                >
                  <option value="mathematiques">Mathématiques</option>
                  <option value="physique">Physique</option>
                  <option value="chimie">Chimie</option>
                </select>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Difficulté <span className="text-red-500">*</span>
              </label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="easy">Facile</option>
                <option value="medium">Moyen</option>
                <option value="hard">Difficile</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Niveau <span className="text-red-500">*</span>
              </label>
              <select
                value={level}
                onChange={(e) => {
                  const nextLevel = e.target.value
                  setLevel(nextLevel)
                  setClassLevel('')
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="lycée">Lycée</option>
                <option value="universite">Université</option>
                <option value="professionnel">Professionnel</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {level === 'lycée' ? 'Classe' : level === 'universite' ? 'Année' : 'Niveau'} <span className="text-red-500">*</span>
              </label>
              <select
                value={classLevel}
                onChange={(e) => setClassLevel(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                {levelOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex space-x-4 mt-6">
            <button
              onClick={() => setCurrentStep(1)}
              className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-3 px-4 rounded-lg transition-colors"
            >
              Retour
            </button>
            <button
              onClick={() => {
                if (!classLevel) {
                  alert('Veuillez sélectionner votre classe/année/niveau')
                  return
                }
                setCurrentStep(3)
              }}
              className="flex-1 bg-primary-600 hover:bg-primary-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors"
            >
              Suivant
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Step 3: Instructions
  if (currentStep === 3) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-xl p-8 max-w-2xl w-full">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Instructions du Quiz</h2>
          <div className="space-y-4 text-gray-700">
            <p>• Vous allez répondre à 20 questions de {subject}</p>
            <p>• Chaque question a 4 options (A, B, C, D)</p>
            <p>• Sélectionnez votre réponse et cliquez sur "Soumettre"</p>
            <p>• Le rapport sera généré automatiquement à la fin</p>
            <p>• Vous recevrez un email avec vos résultats</p>
          </div>
          <div className="flex space-x-4 mt-6">
            <button
              onClick={() => setCurrentStep(2)}
              className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-3 px-4 rounded-lg transition-colors"
            >
              Retour
            </button>
            <button
              onClick={generateQuestions}
              disabled={loading}
              className="flex-1 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-400 text-white font-semibold py-3 px-4 rounded-lg transition-colors"
            >
              {loading ? 'Génération en cours...' : 'Commencer le quiz'}
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Step 4: Loading / Error
  if (currentStep === 4) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-xl p-8 max-w-md w-full text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Génération du quiz en cours...</h2>
          <p className="text-gray-600 mb-6">Veuillez patienter</p>

          {WarningBanner}

          {generationError && (
            <div className="mb-6 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {generationError}
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={cancelGeneration}
              className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-3 px-4 rounded-lg transition-colors"
            >
              Retour
            </button>
            <button
              onClick={generateQuestions}
              disabled={loading}
              className="flex-1 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-400 text-white font-semibold py-3 px-4 rounded-lg transition-colors"
            >
              Réessayer
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Step 5: Ready Screen
  if (currentStep === 5 && showReadyScreen) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-xl p-8 max-w-md w-full text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Prêt à commencer ?</h2>
          <p className="text-gray-700 mb-6">
            Votre quiz de {subject} niveau {level} est prêt.<br />
            Vous aurez {questions.length || 20} questions à répondre.
          </p>
          <button
            onClick={startQuiz}
            className="w-full bg-primary-600 hover:bg-primary-700 text-white font-bold py-4 px-6 rounded-xl"
          >
            Commencer le quiz
          </button>

          <div className="flex gap-3 mt-4">
            <button
              onClick={() => setCurrentStep(3)}
              className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-3 px-4 rounded-lg transition-colors"
            >
              Retour
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Step 5: Quiz Interface
  if (currentStep === 5) {
    return (
      <div key={`step-${currentStep}`} className="h-screen flex flex-col bg-gray-900">
        {/* Header */}
        <div className="bg-gradient-to-r from-primary-600 to-primary-700 px-4 py-3 flex justify-between items-center">
          <div className="flex items-center space-x-4">
            <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253" />
              </svg>
            </div>
            <div className="text-white">
              <div className="text-lg font-semibold">{subject}</div>
              <div className="text-xs text-primary-100">Question {currentQuestionIndex + 1}/{questions.length}</div>
              <div className="mt-1 w-40 h-1.5 bg-white/20 rounded-full overflow-hidden">
                <div
                  className="h-full bg-white/80"
                  style={{ width: `${questions.length ? ((currentQuestionIndex + 1) / questions.length) * 100 : 0}%` }}
                />
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-6">
            <div className="hidden sm:flex items-center space-x-3">
              <div className="w-28 h-16 bg-black/20 rounded overflow-hidden border border-white/20">
                <video
                  ref={setVideoEl}
                  muted
                  playsInline
                  className="w-full h-full object-cover"
                />
              </div>
              <div className="text-white text-xs">
                <div className="font-semibold">Caméra</div>
                {cameraError ? (
                  <div className="text-red-100">{cameraError}</div>
                ) : (
                  <div className="text-primary-100">
                    Visages: {facesCount === null ? '-' : facesCount}
                    {dominantEmotion ? ` | Émotion: ${dominantEmotion}` : ''}
                  </div>
                )}
              </div>
            </div>
            <div className="text-white text-right">
              <div className={`text-xl font-bold ${timeRemaining <= 3 ? 'text-red-200' : ''}`}>{formatTime(timeRemaining)}</div>
              <div className="text-[11px] text-primary-100">Temps restant</div>
            </div>
          </div>
        </div>

        {/* Question */}
        <div className="flex-1 flex">
          {/* Left Side - Question */}
          <div className="flex-1 bg-gray-800 p-8 flex flex-col justify-center">
            <div className="max-w-3xl">
              <h1 className="text-3xl font-bold text-white mb-8">{question.question}</h1>
              <div className="bg-gray-700 rounded-xl p-6">
                <div className="flex items-center space-x-3 mb-3">
                  <svg className="w-6 h-6 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-yellow-400 font-semibold">Conseil</span>
                </div>
                <p className="text-gray-300">Lisez attentivement la question et toutes les options avant de répondre.</p>
              </div>
            </div>
          </div>

          {/* Right Side - Answer Options */}
          <div className="bg-gray-50 p-8 flex flex-col justify-center">
            <div className="max-w-2xl">
              <div className="mb-8">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Choisissez votre réponse</h2>
              </div>

              <div className="space-y-4 mb-8">
                {question?.options?.map((option, idx) => {
                  const displayId = getDisplayOptionId(option, idx)
                  const optionKey = `${question?.id ?? question?.question ?? 'q'}-${idx}-${String(option?.text ?? '')}`
                  return (
                  <button
                    key={optionKey}
                    onClick={() => setSelectedOption(displayId)}
                    className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
                      normalizeOptionId(selectedOption) === displayId
                        ? 'border-primary-600 bg-primary-50 shadow-lg'
                        : 'border-gray-300 bg-white hover:border-primary-400'
                    }`}
                  >
                    <div className="flex items-center space-x-4">
                      <div className={`w-12 h-12 rounded-full flex items-center justify-center font-bold text-lg ${
                        normalizeOptionId(selectedOption) === displayId
                          ? 'bg-primary-600 text-white'
                          : 'bg-gray-200 text-gray-600'
                      }`}>
                        {displayId}
                      </div>
                      <div className="flex-1">
                        <p className={`text-lg font-medium ${
                          normalizeOptionId(selectedOption) === displayId ? 'text-primary-900' : 'text-gray-800'
                        }`}>
                          {option.text}
                        </p>
                      </div>
                      {normalizeOptionId(selectedOption) === displayId && (
                        <svg className="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </div>
                  </button>
                  )
                })}
              </div>

              <div className="border rounded-xl p-4 mb-6 bg-white">
                <div className="flex items-center justify-between mb-2">
                  <div className="text-sm font-semibold text-gray-800">Confiance déclarée (question)</div>
                  <div className="text-sm font-bold text-primary-700">{finalDeclaredConfidence}%</div>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={finalDeclaredConfidence}
                  onChange={(e) => setFinalDeclaredConfidence(Number(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-[11px] text-gray-500 mt-1">
                  <span>Pas sûr</span>
                  <span>Très sûr</span>
                </div>
              </div>

              <button
                onClick={submitAnswer}
                disabled={selectedOption === null || loading}
                className="w-full bg-primary-600 hover:bg-primary-700 disabled:bg-gray-400 text-white font-bold py-4 px-6 rounded-xl flex items-center justify-center"
              >
                {loading ? 'Soumission en cours...' : 'Soumettre la réponse'}
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Step 6: Global confidence before showing results
  if (currentStep === 6) {
    return (
      <div key={`step-${currentStep}`} className="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-xl p-8 max-w-3xl w-full">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Avant de terminer</h1>
            <p className="text-gray-600">Indique ta confiance globale sur ce quiz (0 à 100%).</p>
          </div>

          <div className="border-t pt-6 mb-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-gray-700">Confiance déclarée (globale)</h3>
              <span className="text-sm font-bold text-primary-700">{finalDeclaredConfidence}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={finalDeclaredConfidence}
              onChange={(e) => setFinalDeclaredConfidence(Number(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-[11px] text-gray-500 mt-1">
              <span>Pas sûr</span>
              <span>Très sûr</span>
            </div>

            {cameraError && (
              <div className="mt-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded p-3">
                {cameraError}
              </div>
            )}

            <button
              onClick={confirmGlobalConfidence}
              className="mt-6 w-full bg-primary-600 hover:bg-primary-700 text-white font-bold py-3 px-4 rounded-xl"
            >
              Continuer
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Step 7: Results
  if (currentStep === 7 && results) {
    const declaredPct = Math.round(((results.declared_confidence ?? 0.5) * 100))
    const observedPct = Math.round(((results.observed_confidence ?? 0.5) * 100))
    const dkOn = Boolean(results.bias_flags?.dunning_kruger)
    const impOn = Boolean(results.bias_flags?.impostor)
    const hasBiasNotes = Array.isArray(results.bias_notes) && results.bias_notes.length > 0

    return (
      <div key={`step-${currentStep}`} className="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-xl p-8 max-w-4xl w-full">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-4">Quiz Terminé !</h1>
            <div className="flex justify-center space-x-8 mb-6">
              <div className="text-center">
                <div className="text-4xl font-bold text-primary-600">{results.percentage}%</div>
                <div className="text-gray-600">Score global</div>
              </div>
              <div className="text-center">
                <div className="text-4xl font-bold text-primary-600">{results.score}</div>
                <div className="text-gray-600">Points obtenus</div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
            <div className="border rounded-xl p-4 bg-gray-50">
              <div className="text-sm font-semibold text-gray-700">Confiance déclarée</div>
              <div className="text-2xl font-bold text-primary-700">{declaredPct}%</div>
              <div className="text-xs text-gray-600 mt-1">Auto-évaluation (globale)</div>
            </div>
            <div className="border rounded-xl p-4 bg-gray-50">
              <div className="text-sm font-semibold text-gray-700">Confiance observée</div>
              <div className="text-2xl font-bold text-primary-700">{observedPct}%</div>
              <div className="text-xs text-gray-600 mt-1">Calculée à partir des émotions</div>
            </div>
          </div>

          <div className="border rounded-xl p-4 mb-8">
            <div className="text-sm font-semibold text-gray-800 mb-3">Biais cognitifs (détection)</div>
            <div className="flex flex-wrap gap-2">
              <span className={`px-3 py-1 rounded-full text-sm font-semibold ${dkOn ? 'bg-red-100 text-red-800 border border-red-200' : 'bg-gray-100 text-gray-700 border border-gray-200'}`}>
                Dunning-Kruger: {dkOn ? 'détecté' : 'non détecté'}
              </span>
              <span className={`px-3 py-1 rounded-full text-sm font-semibold ${impOn ? 'bg-amber-100 text-amber-800 border border-amber-200' : 'bg-gray-100 text-gray-700 border border-gray-200'}`}>
                Imposteur: {impOn ? 'détecté' : 'non détecté'}
              </span>
            </div>

            {hasBiasNotes && (
              <div className="mt-4 text-sm text-gray-700">
                <div className="font-semibold mb-2">Notes</div>
                <ul className="list-disc pl-5 space-y-1">
                  {results.bias_notes.slice(0, 5).map((n, idx) => (
                    <li key={`bias-note-${idx}`}>{n}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="border-t pt-6">
            <button
              onClick={async () => {
                downloadReport()
              }}
              className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-4 px-6 rounded-xl flex items-center justify-center mb-4"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Télécharger le rapport d'évaluation
            </button>
            <button
              onClick={sendEmailReport}
              className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-4 px-6 rounded-xl flex items-center justify-center mb-4"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h10m-7 4h10M7 16h10" />
              </svg>
              Envoyer le rapport par email
            </button>
            <div className="mt-8" />
          </div>
        </div>
      </div>
    )
  }

  return null
}

export default QuizPage
