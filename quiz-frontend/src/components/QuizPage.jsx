import { useState, useEffect, useRef } from 'react'
import QuizInterfacePage from './QuizInterfacePage'
import WebcamAnalyzer from './WebcamAnalyzer'

const API_BASE_URL = 'http://localhost:8000'

function QuizPage({ onBackToHome }) {
  // Multi-step state
  const [currentStep, setCurrentStep] = useState(1)
  
  // User information
  const [userName, setUserName] = useState('')
  const [userAge, setUserAge] = useState('')
  const [userAcademicLevel, setUserAcademicLevel] = useState('lycée')
  const [userEmail, setUserEmail] = useState('')
  
  // Quiz settings
  const [subject, setSubject] = useState('mathématiques')
  const [level, setLevel] = useState('lycée')
  const [userInfo, setUserInfo] = useState('')
  
  // Quiz state
  const [questions, setQuestions] = useState([])
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [question, setQuestion] = useState(null)
  const [loading, setLoading] = useState(false)
  const [confidence, setConfidence] = useState(50)
  const [selectedOption, setSelectedOption] = useState(null)
  const [sessionId, setSessionId] = useState(null)
  const [error, setError] = useState(null)
  const [showResults, setShowResults] = useState(false)
  const [results, setResults] = useState(null)
  const [answers, setAnswers] = useState([])
  
  // Timer state
  const [timeRemaining, setTimeRemaining] = useState(1200) // 20 minutes for 10 questions
  const [testStarted, setTestStarted] = useState(false)
  const [testEnded, setTestEnded] = useState(false)
  const timerRef = useRef(null)
  
  // Webcam behavioral tracking
  const webcamRef = useRef(null)
  const [webcamEnabled, setWebcamEnabled] = useState(true)
  
  // Interaction tracking
  const [interactionData, setInteractionData] = useState(null)
  
  // Camera permission
  const [cameraPermissionGranted, setCameraPermissionGranted] = useState(false)
  const [requestingCamera, setRequestingCamera] = useState(false)
  
  // Ready to start screen (before countdown)
  const [showReadyScreen, setShowReadyScreen] = useState(false)
  
  // Countdown before quiz starts
  const [showCountdown, setShowCountdown] = useState(false)
  const [countdownValue, setCountdownValue] = useState(5)
  
  // Fullscreen warning
  const [showFullscreenWarning, setShowFullscreenWarning] = useState(false)
  const [fullscreenWarningTime, setFullscreenWarningTime] = useState(10)
  const fullscreenWarningTimerRef = useRef(null)
  
  // Confidence modal (shown after answer submission)
  const [showConfidenceModal, setShowConfidenceModal] = useState(false)
  const [pendingAnswerData, setPendingAnswerData] = useState(null)

  // Fullscreen management with 10-second warning
  useEffect(() => {
    if (testStarted && !testEnded) {
      const handleFullscreenChange = () => {
        if (!document.fullscreenElement) {
          // Clear any existing timer first
          if (fullscreenWarningTimerRef.current) {
            clearInterval(fullscreenWarningTimerRef.current)
          }
          
          // User exited fullscreen - show 10 second warning
          setShowFullscreenWarning(true)
          setFullscreenWarningTime(10)
          
          // Start countdown timer
          let countdown = 10
          fullscreenWarningTimerRef.current = setInterval(() => {
            countdown--
            setFullscreenWarningTime(countdown)
            
            if (countdown <= 0) {
              // Time's up - end test automatically
              clearInterval(fullscreenWarningTimerRef.current)
              endTest('Vous n\'avez pas repris le mode plein écran. Le test est terminé.')
            }
          }, 1000)
        } else if (document.fullscreenElement) {
          // User returned to fullscreen - cancel warning
          setShowFullscreenWarning(false)
          if (fullscreenWarningTimerRef.current) {
            clearInterval(fullscreenWarningTimerRef.current)
            fullscreenWarningTimerRef.current = null
          }
        }
      }

      document.addEventListener('fullscreenchange', handleFullscreenChange)
      document.addEventListener('webkitfullscreenchange', handleFullscreenChange)
      document.addEventListener('mozfullscreenchange', handleFullscreenChange)
      document.addEventListener('MSFullscreenChange', handleFullscreenChange)

      return () => {
        document.removeEventListener('fullscreenchange', handleFullscreenChange)
        document.removeEventListener('webkitfullscreenchange', handleFullscreenChange)
        document.removeEventListener('mozfullscreenchange', handleFullscreenChange)
        document.removeEventListener('MSFullscreenChange', handleFullscreenChange)
        if (fullscreenWarningTimerRef.current) {
          clearInterval(fullscreenWarningTimerRef.current)
        }
      }
    }
  }, [testStarted, testEnded])

  // Timer management (pauses during fullscreen warning)
  useEffect(() => {
    if (testStarted && !testEnded && timeRemaining > 0 && !showFullscreenWarning) {
      timerRef.current = setInterval(() => {
        setTimeRemaining((prev) => {
          if (prev <= 1) {
            endTest('Le temps est écoulé !')
            return 0
          }
          return prev - 1
        })
      }, 1000)

      return () => {
        if (timerRef.current) {
          clearInterval(timerRef.current)
        }
      }
    } else if (showFullscreenWarning && timerRef.current) {
      // Pause timer during fullscreen warning
      clearInterval(timerRef.current)
    }
  }, [testStarted, testEnded, timeRemaining, showFullscreenWarning])
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (fullscreenWarningTimerRef.current) {
        clearInterval(fullscreenWarningTimerRef.current)
      }
    }
  }, [])

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const endTest = (message) => {
    setTestEnded(true)
    setTestStarted(false)
    if (timerRef.current) {
      clearInterval(timerRef.current)
    }
    // Exit fullscreen
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(err => console.error(err))
    }
    alert(message)
  }

  const handleUserInfoSubmit = (e) => {
    e.preventDefault()
    setCurrentStep(2)
  }

  const handlePreferencesSubmit = () => {
    setCurrentStep(3) // Move to instructions
  }
  
  const requestCameraPermission = async () => {
    setRequestingCamera(true)
    try {
      // Request camera access
      const stream = await navigator.mediaDevices.getUserMedia({ video: true })
      // Stop the stream immediately, we just needed permission
      stream.getTracks().forEach(track => track.stop())
      setCameraPermissionGranted(true)
      // Proceed to generate questions
      await generateQuestions()
    } catch (error) {
      console.error('Camera permission denied:', error)
      alert('L\'accès à la caméra est requis pour le suivi comportemental. Veuillez autoriser l\'accès à la caméra.')
      setRequestingCamera(false)
    }
  }

  const startTest = async () => {
    // First request camera permission
    await requestCameraPermission()
  }
  
  const generateQuestions = async () => {
    // Generate 10 questions from backend
    setLoading(true)
    setError(null)
    setCurrentStep(4) // Move to quiz (shows loading)
      
      try {
        const response = await fetch(`${API_BASE_URL}/generate-quiz?num_questions=10`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            subject: subject,
            level: level,
            user_info: userInfo
          })
        })
        
        if (!response.ok) {
          throw new Error('Failed to generate quiz')
        }
        
        const data = await response.json()
        
        // Format the questions
        const formattedQuestions = data.questions.map(q => ({
          id: q.id,
          question: q.question,
          options: q.options.map((opt, idx) => ({
            id: String.fromCharCode(65 + idx), // A, B, C, D
            text: opt
          }))
        }))
        
        setQuestions(formattedQuestions)
        setQuestion(formattedQuestions[0])
        setSessionId(data.session_id)
        
        // Show ready screen - wait for user to click start
        setShowReadyScreen(true)
        
      } catch (error) {
        console.error('Error generating quiz:', error)
        setError('Failed to generate quiz. Please try again.')
        alert('Erreur lors de la génération du quiz. Veuillez réessayer.')
        setCurrentStep(3) // Go back to instructions
      } finally {
        setLoading(false)
        setRequestingCamera(false)
      }
  }
  
  const userClickedStart = async () => {
    // First enter fullscreen
    const elem = document.documentElement
    try {
      if (elem.requestFullscreen) {
        await elem.requestFullscreen()
      } else if (elem.webkitRequestFullscreen) {
        await elem.webkitRequestFullscreen()
      } else if (elem.mozRequestFullScreen) {
        await elem.mozRequestFullScreen()
      } else if (elem.msRequestFullscreen) {
        await elem.msRequestFullscreen()
      }
      
      // Hide ready screen and show countdown
      setShowReadyScreen(false)
      setShowCountdown(true)
      setCountdownValue(5)
      
      // Start countdown
      const countdownInterval = setInterval(() => {
        setCountdownValue((prev) => {
          if (prev <= 1) {
            clearInterval(countdownInterval)
            // Start the test
            setShowCountdown(false)
            setTestStarted(true)
            return 0
          }
          return prev - 1
        })
      }, 1000)
      
    } catch (error) {
      alert('Le mode plein écran est requis pour commencer le test.')
      setCurrentStep(3)
    }
  }

  const submitAnswer = async () => {
    if (selectedOption === null) {
      alert('Veuillez sélectionner une réponse avant de soumettre.')
      return
    }
    
    setLoading(true)
    
    try {
      // Convert A, B, C, D to 0, 1, 2, 3
      const answerIndex = selectedOption.charCodeAt(0) - 65
      const currentQuestion = questions[currentQuestionIndex]
      
      // Collect behavioral data from webcam
      let behavioralData = {}
      if (webcamEnabled && webcamRef.current) {
        const metrics = webcamRef.current.getCurrentMetrics()
        behavioralData = {
          ...metrics,
          interaction: interactionData || {}
        }
        // Reset metrics for next question
        webcamRef.current.resetMetrics()
      }
      
      // Submit answer with default confidence (will be updated at the end)
      const response = await fetch(`${API_BASE_URL}/submit-answer`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          question_id: currentQuestion.id,
          selected_answer: answerIndex,
          confidence: 50, // Default value, will ask at end
          behavioral_data: behavioralData
        })
      })
      
      if (!response.ok) {
        throw new Error('Failed to submit answer')
      }
      
      const data = await response.json()
      
      // Store answer without confidence for now
      setAnswers([...answers, {
        questionIndex: currentQuestionIndex,
        selectedOption: selectedOption,
        confidence: null, // Will be set at the end
        isCorrect: data.correct
      }])
      
      // Move to next question or show confidence modal for entire quiz
      if (currentQuestionIndex < questions.length - 1) {
        setCurrentQuestionIndex(currentQuestionIndex + 1)
        setQuestion(questions[currentQuestionIndex + 1])
        setSelectedOption(null)
        setInteractionData(null) // Reset interaction data
      } else {
        // Quiz completed - show confidence modal for overall quiz
        setShowConfidenceModal(true)
      }
    } catch (error) {
      console.error('Error submitting answer:', error)
      alert('Erreur lors de la soumission de la réponse. Veuillez réessayer.')
    } finally {
      setLoading(false)
    }
  }
  
  const submitAnswerWithConfidence = async () => {
    setShowConfidenceModal(false)
    setLoading(true)
    
    try {
      // Store the overall confidence level
      // Update all answers with the confidence value
      const updatedAnswers = answers.map(ans => ({
        ...ans,
        confidence: confidence
      }))
      setAnswers(updatedAnswers)
      
      // Send the confidence level to the backend
      await fetch(`${API_BASE_URL}/update-confidence`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          confidence: confidence
        })
      })
      
      // Fetch and show results
      await showQuizResults()
    } catch (error) {
      console.error('Error:', error)
      alert('Erreur. Veuillez réessayer.')
    } finally {
      setLoading(false)
    }
  }

  const showQuizResults = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/quiz-results/${sessionId}`)
      
      if (!response.ok) {
        throw new Error('Failed to fetch results')
      }
      
      const data = await response.json()
      console.log('Results data:', data)
      console.log('Question results:', data.question_results)
      setResults(data)
      setShowResults(true)
      setTestStarted(false)
      setTestEnded(true)
      
      // Exit fullscreen
      if (document.fullscreenElement) {
        document.exitFullscreen().catch(err => console.error(err))
      }
      
      // Stop timer
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
    } catch (error) {
      console.error('Error fetching results:', error)
      alert('Erreur lors du chargement des résultats.')
    }
  }

  if (currentStep === 4 && !testEnded && !showResults) {
    // Show ready screen - wait for user to click start
    if (showReadyScreen) {
      return (
        <div className="h-screen flex flex-col items-center justify-center bg-gradient-to-br from-primary-900 via-primary-800 to-primary-900">
          <div className="text-center max-w-2xl mx-auto px-6">
            <div className="mb-8">
              <div className="w-24 h-24 bg-white bg-opacity-20 rounded-full flex items-center justify-center mx-auto mb-6">
                <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h2 className="text-4xl font-bold text-white mb-4">Questions prêtes !</h2>
              <p className="text-primary-200 text-lg mb-8">
                Votre quiz de {questions.length} questions est prêt. 
                <br />
                Cliquez sur le bouton ci-dessous pour commencer.
              </p>
            </div>
            
            <div className="bg-white bg-opacity-10 rounded-xl p-6 mb-8 text-left">
              <h3 className="text-white font-semibold mb-3 flex items-center">
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Rappel important :
              </h3>
              <ul className="text-primary-100 text-sm space-y-2">
                <li className="flex items-start">
                  <span className="mr-2">•</span>
                  <span>Le quiz se déroulera en mode plein écran</span>
                </li>
                <li className="flex items-start">
                  <span className="mr-2">•</span>
                  <span>Vous aurez 20 minutes pour répondre aux {questions.length} questions</span>
                </li>
                <li className="flex items-start">
                  <span className="mr-2">•</span>
                  <span>Ne quittez pas le mode plein écran sous peine de fin de test</span>
                </li>
                <li className="flex items-start">
                  <span className="mr-2">•</span>
                  <span>Votre comportement sera analysé via la caméra</span>
                </li>
              </ul>
            </div>
            
            <button
              onClick={userClickedStart}
              className="bg-white hover:bg-gray-100 text-primary-900 font-bold py-4 px-12 rounded-xl shadow-2xl hover:shadow-3xl transform hover:scale-105 transition-all duration-200 text-lg"
            >
              <span className="flex items-center">
                <svg className="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Commencer le quiz
              </span>
            </button>
          </div>
        </div>
      )
    }
    
    // Show countdown screen
    if (showCountdown) {
      return (
        <div className="h-screen flex flex-col items-center justify-center bg-gradient-to-br from-primary-900 via-primary-800 to-primary-900 px-4">
          <div className="text-center">
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-6 sm:mb-8">Préparez-vous !</h2>
            <div className="relative w-32 h-32 sm:w-40 sm:h-40 md:w-48 md:h-48 mx-auto mb-6 sm:mb-8">
              <div className="absolute inset-0 border-6 sm:border-8 border-primary-300 rounded-full"></div>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-6xl sm:text-7xl md:text-9xl font-bold text-white">{countdownValue}</span>
              </div>
            </div>
            <p className="text-primary-200 text-base sm:text-lg md:text-xl px-4">Le quiz démarre dans {countdownValue} seconde{countdownValue > 1 ? 's' : ''}...</p>
          </div>
        </div>
      )
    }
    
    if (loading || !question) {
      return (
        <div className="h-screen flex flex-col items-center justify-center bg-gradient-to-br from-primary-900 via-primary-800 to-primary-900 px-4">
          <div className="text-center">
            <div className="relative w-24 h-24 sm:w-32 sm:h-32 mx-auto mb-6 sm:mb-8">
              <div className="absolute inset-0 border-6 sm:border-8 border-primary-300 border-t-transparent rounded-full animate-spin"></div>
              <div className="absolute inset-4 border-6 sm:border-8 border-primary-400 border-t-transparent rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1s' }}></div>
              <div className="absolute inset-0 flex items-center justify-center">
                <svg className="w-8 h-8 sm:w-12 sm:h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
            </div>
            <h2 className="text-xl sm:text-2xl md:text-3xl font-bold text-white mb-3 sm:mb-4 px-4">Préparation de votre quiz...</h2>
            <div className="flex items-center justify-center space-x-2">
              <div className="w-3 h-3 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '0s' }}></div>
              <div className="w-3 h-3 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              <div className="w-3 h-3 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
            </div>
          </div>
        </div>
      )
    }
    
    return (
      <>
        <QuizInterfacePage
          subject={subject}
          timeRemaining={timeRemaining}
          formatTime={formatTime}
          question={question}
          selectedOption={selectedOption}
        setSelectedOption={setSelectedOption}
        submitAnswer={submitAnswer}
        loading={loading}
        currentQuestion={currentQuestionIndex + 1}
        totalQuestions={questions.length}
        onInteractionData={setInteractionData}
      />
      {webcamEnabled && (
        <div style={{ display: 'none' }}>
          <WebcamAnalyzer
            isActive={testStarted && !testEnded}
            onMetricsUpdate={(methods) => { webcamRef.current = methods }}
          />
        </div>
      )}
      
      {/* Fullscreen Warning Modal */}
      {showFullscreenWarning && (
        <div className="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 sm:p-8 max-w-md w-full mx-4 text-center shadow-2xl">
            <div className="w-16 h-16 sm:w-20 sm:h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4 sm:mb-6">
              <svg className="w-8 h-8 sm:w-10 sm:h-10 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h3 className="text-xl sm:text-2xl font-bold text-gray-900 mb-3 sm:mb-4">Attention !</h3>
            <p className="text-sm sm:text-base text-gray-700 mb-4 sm:mb-6">
              Vous avez quitté le mode plein écran. Veuillez revenir en mode plein écran dans :
            </p>
            <div className="text-4xl sm:text-5xl md:text-6xl font-bold text-red-600 mb-4 sm:mb-6">{fullscreenWarningTime}</div>
            <p className="text-xs sm:text-sm text-gray-500">Le test sera automatiquement terminé si vous ne revenez pas en mode plein écran.</p>
            <button
              onClick={async () => {
                const elem = document.documentElement
                try {
                  if (elem.requestFullscreen) {
                    await elem.requestFullscreen()
                  } else if (elem.webkitRequestFullscreen) {
                    await elem.webkitRequestFullscreen()
                  } else if (elem.mozRequestFullScreen) {
                    await elem.mozRequestFullScreen()
                  } else if (elem.msRequestFullscreen) {
                    await elem.msRequestFullscreen()
                  }
                } catch (error) {
                  console.error('Error entering fullscreen:', error)
                }
              }}
              className="mt-6 bg-primary-600 hover:bg-primary-700 text-white font-bold py-3 px-6 rounded-lg transition-colors"
            >
              Revenir en plein écran
            </button>
          </div>
        </div>
      )}
      
      {/* Confidence Modal - Asked at end of quiz */}
      {showConfidenceModal && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-8 max-w-lg mx-4 shadow-2xl">
            <div className="mb-6 text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-2">
                Quiz terminé !
              </h3>
              <p className="text-gray-600">
                Évaluez votre niveau de confiance global pour ce quiz
              </p>
            </div>
            
            <div className="mb-8">
              <div className="text-center mb-4">
                <span className="text-5xl font-bold text-primary-600">{confidence}%</span>
              </div>
              
              <input
                type="range"
                min="0"
                max="100"
                value={confidence}
                onChange={(e) => setConfidence(Number(e.target.value))}
                className="w-full h-4 bg-primary-200 rounded-lg appearance-none cursor-pointer mb-4"
                style={{
                  background: `linear-gradient(to right, #16a34a 0%, #16a34a ${confidence}%, #bbf7d0 ${confidence}%, #bbf7d0 100%)`
                }}
              />
              
              <div className="flex justify-between text-sm text-gray-600">
                <span>Pas confiant du tout</span>
                <span>Très confiant</span>
              </div>
            </div>
            
            <div className="bg-primary-50 rounded-lg p-4 mb-6">
              <p className="text-sm text-gray-700 text-center">
                Évaluez votre niveau de confiance global concernant l'ensemble de vos réponses.
              </p>
            </div>
            
            <button
              onClick={submitAnswerWithConfidence}
              className="w-full bg-gradient-to-r from-primary-600 to-primary-700 hover:from-primary-700 hover:to-primary-800 text-white font-bold py-4 px-8 rounded-xl shadow-lg hover:shadow-xl transform hover:-translate-y-1 transition-all duration-200"
            >
              Voir mes résultats
            </button>
          </div>
        </div>
      )}
      </>
    )
  }

  // Results Page
  if (showResults && results) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-primary-50">
        {/* Header */}
        <header className="bg-white shadow-sm border-b border-primary-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div className="flex items-center space-x-3 sm:space-x-4">
                <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-br from-primary-600 to-primary-700 rounded-xl flex items-center justify-center">
                  <svg className="w-6 h-6 sm:w-7 sm:h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <h1 className="text-lg sm:text-2xl font-bold text-primary-800">Résultats du Quiz</h1>
                  <p className="text-xs sm:text-sm text-primary-600">SIMCO - Évaluation Cognitive</p>
                </div>
              </div>
              <button
                onClick={onBackToHome}
                className="bg-primary-600 hover:bg-primary-700 text-white font-semibold py-2 px-4 sm:px-6 rounded-lg shadow-md hover:shadow-lg transform hover:-translate-y-0.5 transition-all duration-200 text-sm sm:text-base"
              >
                Retour à l'accueil
              </button>
            </div>
          </div>
        </header>

        <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-12">
          {/* Score Card */}
          <div className="bg-white rounded-2xl shadow-xl border-2 border-primary-200 p-4 sm:p-8 mb-6 sm:mb-8">
            <div className="text-center mb-6 sm:mb-8">
              <div className={`w-24 h-24 sm:w-32 sm:h-32 mx-auto rounded-full flex items-center justify-center mb-4 sm:mb-6 ${
                results.color === 'success' ? 'bg-green-100' :
                results.color === 'good' ? 'bg-blue-100' :
                results.color === 'average' ? 'bg-yellow-100' :
                'bg-red-100'
              }`}>
                <div className="text-center">
                  <div className={`text-4xl sm:text-5xl font-bold ${
                    results.color === 'success' ? 'text-green-600' :
                    results.color === 'good' ? 'text-blue-600' :
                    results.color === 'average' ? 'text-yellow-600' :
                    'text-red-600'
                  }`}>
                    {results.percentage}%
                  </div>
                </div>
              </div>
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-gray-900 mb-2 sm:mb-3 px-2">{results.level}</h2>
              <p className="text-base sm:text-lg md:text-xl text-gray-600 mb-4 sm:mb-6 px-4">{results.message}</p>
              <div className="inline-flex items-center space-x-4 sm:space-x-8 bg-gray-50 px-4 sm:px-8 py-3 sm:py-4 rounded-xl flex-wrap justify-center">
                <div className="text-center">
                  <div className="text-2xl sm:text-3xl font-bold text-primary-600">{results.score}</div>
                  <div className="text-xs sm:text-sm text-gray-500">Correctes</div>
                </div>
                <div className="w-px h-8 sm:h-12 bg-gray-300"></div>
                <div className="text-center">
                  <div className="text-2xl sm:text-3xl font-bold text-gray-400">{results.total_questions - results.score}</div>
                  <div className="text-xs sm:text-sm text-gray-500">Incorrectes</div>
                </div>
                <div className="w-px h-8 sm:h-12 bg-gray-300"></div>
                <div className="text-center">
                  <div className="text-2xl sm:text-3xl font-bold text-gray-700">{results.total_questions}</div>
                  <div className="text-xs sm:text-sm text-gray-500">Total</div>
                </div>
              </div>
            </div>

            {/* Performance Analysis */}
            <div className="border-t border-gray-200 pt-6 sm:pt-8">
              <h3 className="text-xl sm:text-2xl font-bold text-gray-900 mb-3 sm:mb-4 flex items-center">
                <svg className="w-6 h-6 sm:w-7 sm:h-7 mr-2 sm:mr-3 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                Analyse de Performance
              </h3>
              <div className="bg-gradient-to-br from-primary-50 to-white p-6 rounded-xl border border-primary-100">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="font-semibold text-gray-800 mb-3 flex items-center">
                      <span className={`w-3 h-3 rounded-full mr-2 ${
                        results.color === 'success' ? 'bg-green-500' :
                        results.color === 'good' ? 'bg-blue-500' :
                        results.color === 'average' ? 'bg-yellow-500' :
                        'bg-red-500'
                      }`}></span>
                      Points Forts
                    </h4>
                    <ul className="space-y-2 text-gray-700">
                      {results.score >= results.total_questions * 0.7 && (
                        <li className="flex items-start">
                          <svg className="w-5 h-5 text-green-500 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          Bonne maîtrise du sujet
                        </li>
                      )}
                      {results.answered_count === results.total_questions && (
                        <li className="flex items-start">
                          <svg className="w-5 h-5 text-green-500 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          Quiz complété intégralement
                        </li>
                      )}
                      {results.score > 0 && (
                        <li className="flex items-start">
                          <svg className="w-5 h-5 text-green-500 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          Capacité à répondre correctement
                        </li>
                      )}
                    </ul>
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-800 mb-3 flex items-center">
                      <span className="w-3 h-3 rounded-full bg-amber-500 mr-2"></span>
                      Axes d'Amélioration
                    </h4>
                    <ul className="space-y-2 text-gray-700">
                      {results.score < results.total_questions * 0.5 && (
                        <li className="flex items-start">
                          <svg className="w-5 h-5 text-amber-500 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                          </svg>
                          Renforcer les bases fondamentales
                        </li>
                      )}
                      {results.score < results.total_questions && (
                        <li className="flex items-start">
                          <svg className="w-5 h-5 text-amber-500 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                          </svg>
                          Réviser les questions manquées
                        </li>
                      )}
                      <li className="flex items-start">
                        <svg className="w-5 h-5 text-amber-500 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        Pratiquer régulièrement
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Recommendations */}
          <div className="bg-white rounded-2xl shadow-xl border border-primary-200 p-4 sm:p-6 md:p-8 mb-6 sm:mb-8">
            <h3 className="text-xl sm:text-2xl font-bold text-gray-900 mb-4 sm:mb-6 flex items-center">
              <svg className="w-6 h-6 sm:w-7 sm:h-7 mr-2 sm:mr-3 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              Recommandations
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {results.recommendations.map((rec, idx) => (
                <div key={idx} className="flex items-start p-4 bg-primary-50 rounded-lg border border-primary-100">
                  <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center flex-shrink-0 mr-3">
                    <span className="text-white font-bold">{idx + 1}</span>
                  </div>
                  <p className="text-gray-700 leading-relaxed">{rec}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Behavioral Analysis */}
          {results.behavioral_analysis && (
            <div className="bg-gradient-to-br from-purple-50 to-indigo-50 rounded-2xl shadow-xl border-2 border-purple-200 p-8 mb-8">
              <h3 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
                <svg className="w-7 h-7 mr-3 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                Analyse Comportementale
                <span className="ml-3 px-3 py-1 bg-purple-600 text-white text-xs font-semibold rounded-full">SIMCO AI</span>
              </h3>
              
              {/* Metrics Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-white rounded-xl p-3 sm:p-4 border border-purple-200 shadow-sm">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs sm:text-sm font-medium text-gray-600">Niveau de Stress</span>
                    <div className={`w-3 h-3 rounded-full ${
                      results.behavioral_analysis.overall_stress_level === 'low' ? 'bg-green-500' :
                      results.behavioral_analysis.overall_stress_level === 'medium' ? 'bg-yellow-500' :
                      'bg-red-500'
                    }`}></div>
                  </div>
                  <p className="text-xl sm:text-xl sm:text-2xl font-bold text-gray-900 capitalize">{
                    results.behavioral_analysis.overall_stress_level === 'low' ? 'Faible' :
                    results.behavioral_analysis.overall_stress_level === 'medium' ? 'Modéré' :
                    'Élevé'
                  }</p>
                  <p className="text-xs text-gray-500 mt-1">{results.behavioral_analysis.avg_blink_rate.toFixed(1)} clignements/min</p>
                </div>
                
                <div className="bg-white rounded-xl p-3 sm:p-4 border border-purple-200 shadow-sm">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs sm:text-sm font-medium text-gray-600">Stabilité du Regard</span>
                    <div className={`w-3 h-3 rounded-full ${
                      results.behavioral_analysis.avg_gaze_stability > 0.8 ? 'bg-green-500' :
                      results.behavioral_analysis.avg_gaze_stability > 0.6 ? 'bg-yellow-500' :
                      'bg-red-500'
                    }`}></div>
                  </div>
                  <p className="text-xl sm:text-2xl font-bold text-gray-900">{(results.behavioral_analysis.avg_gaze_stability * 100).toFixed(0)}%</p>
                  <p className="text-xs text-gray-500 mt-1">Concentration</p>
                </div>
                
                <div className="bg-white rounded-xl p-3 sm:p-4 border border-purple-200 shadow-sm">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs sm:text-sm font-medium text-gray-600">Calibration Confiance</span>
                    <div className={`w-3 h-3 rounded-full ${
                      results.behavioral_analysis.confidence_calibration === 'well_calibrated' ? 'bg-green-500' :
                      results.behavioral_analysis.confidence_calibration === 'underconfident' ? 'bg-yellow-500' :
                      'bg-orange-500'
                    }`}></div>
                  </div>
                  <p className="text-base sm:text-lg font-bold text-gray-900 capitalize">{
                    results.behavioral_analysis.confidence_calibration === 'well_calibrated' ? 'Bonne' :
                    results.behavioral_analysis.confidence_calibration === 'underconfident' ? 'Sous-confiance' :
                    'Surconfiance'
                  }</p>
                  <p className="text-xs text-gray-500 mt-1">Auto-évaluation</p>
                </div>
              </div>
              
              {/* Behavioral Insights */}
              {results.behavioral_insights && results.behavioral_insights.length > 0 && (
                <div className="bg-white rounded-xl p-4 sm:p-6 border border-purple-200">
                  <h4 className="text-sm sm:text-base font-semibold text-gray-800 mb-3 sm:mb-4 flex items-center">
                    <svg className="w-4 h-4 sm:w-5 sm:h-5 mr-2 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Observations Comportementales
                  </h4>
                  <div className="space-y-2 sm:space-y-3">
                    {results.behavioral_insights.map((insight, idx) => (
                      <div key={idx} className="flex items-start p-2 sm:p-3 bg-purple-50 rounded-lg">
                        <svg className="w-4 h-4 sm:w-5 sm:h-5 text-purple-600 mr-2 sm:mr-3 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                        <p className="text-gray-700 text-xs sm:text-sm">{insight}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              <div className="mt-6 p-4 bg-white/50 rounded-lg border border-purple-200">
                <p className="text-xs text-gray-600 flex items-center">
                  <svg className="w-4 h-4 mr-2 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  L'analyse comportementale utilise la reconnaissance faciale pour évaluer votre niveau d'engagement, de stress et de confiance pendant le quiz.
                </p>
              </div>
            </div>
          )}

          {/* Detailed Results */}
          <div className="bg-white rounded-2xl shadow-xl border border-primary-200 p-4 sm:p-6 md:p-8">
            <h3 className="text-xl sm:text-2xl font-bold text-gray-900 mb-4 sm:mb-6 flex items-center">
              <svg className="w-6 h-6 sm:w-7 sm:h-7 mr-2 sm:mr-3 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
              </svg>
              Détails des Questions
            </h3>
            <div className="space-y-4">
              {results.question_results.map((qr, idx) => {
                const wasAnswered = qr.user_answer !== null && qr.user_answer !== undefined
                const cardColor = !wasAnswered ? 'border-gray-300 bg-gray-50' : 
                                qr.is_correct ? 'border-green-200 bg-green-50' : 
                                'border-red-200 bg-red-50'
                const iconColor = !wasAnswered ? 'bg-gray-400' :
                                qr.is_correct ? 'bg-green-500' : 'bg-red-500'
                
                return (
                  <div key={idx} className={`border-2 rounded-xl p-6 ${cardColor}`}>
                    <div className="flex items-start justify-between mb-4">
                      <h4 className="font-semibold text-gray-900 flex-1 pr-4">
                        <span className="text-primary-600">Question {idx + 1}:</span> {qr.question}
                      </h4>
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${iconColor}`}>
                        {!wasAnswered ? (
                          <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                          </svg>
                        ) : qr.is_correct ? (
                          <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        ) : (
                          <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        )}
                      </div>
                    </div>
                  <div className="space-y-2 mb-4">
                    {qr.options.map((opt, optIdx) => {
                      const letter = String.fromCharCode(65 + optIdx)
                      const isCorrect = optIdx === qr.correct_answer
                      const isSelected = qr.user_answer !== null && qr.user_answer !== undefined && optIdx === qr.user_answer
                      const wasNotAnswered = qr.user_answer === null || qr.user_answer === undefined
                      
                      return (
                        <div key={optIdx} className={`p-3 rounded-lg ${
                          isCorrect ? 'bg-green-100 border-2 border-green-400' :
                          isSelected && !isCorrect ? 'bg-red-100 border-2 border-red-400' :
                          'bg-white border border-gray-200'
                        }`}>
                          <span className="font-semibold">{letter})</span> {opt}
                          {isCorrect && (
                            <span className="ml-2 text-green-600 font-semibold">✓ Bonne réponse</span>
                          )}
                          {isSelected && !isCorrect && (
                            <span className="ml-2 text-red-600 font-semibold">✗ Votre réponse</span>
                          )}
                        </div>
                      )
                    })}
                    {(qr.user_answer === null || qr.user_answer === undefined) && (
                      <p className="text-sm text-gray-500 italic mt-2">Vous n'avez pas répondu à cette question</p>
                    )}
                  </div>
                  <div className="bg-white border-l-4 border-primary-500 p-3 sm:p-4 rounded">
                    <p className="text-xs sm:text-sm font-semibold text-gray-700 mb-1">💡 Explication:</p>
                    <p className="text-xs sm:text-base text-gray-600">{qr.explanation}</p>
                  </div>
                </div>
              )})}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="mt-6 sm:mt-8 flex justify-center px-4">
            <button
              onClick={onBackToHome}
              className="w-full sm:w-auto bg-gradient-to-r from-primary-600 to-primary-700 hover:from-primary-700 hover:to-primary-800 text-white font-semibold py-3 sm:py-4 px-6 sm:px-8 rounded-lg shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200 text-sm sm:text-base"
            >
              Retour à l'accueil
            </button>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-primary-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-primary-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={onBackToHome}
                className="text-primary-600 hover:text-primary-700 flex items-center space-x-2 transition-colors"
              >
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
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-primary-500 rounded-full animate-pulse"></div>
              <span className="text-sm text-primary-700 font-medium">En ligne</span>
            </div>
          </div>
        </div>
      </header>

      {/* Progress Indicator */}
      {currentStep < 4 && (
        <div className="bg-white border-b border-primary-200">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="flex items-center justify-between">
              {[1, 2, 3].map((step) => (
                <div key={step} className="flex items-center flex-1">
                  <div className="flex items-center relative">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-all ${
                      currentStep >= step 
                        ? 'bg-primary-600 text-white' 
                        : 'bg-gray-200 text-gray-500'
                    }`}>
                      {currentStep > step ? (
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      ) : (
                        step
                      )}
                    </div>
                    <span className={`ml-3 font-medium ${
                      currentStep >= step ? 'text-primary-700' : 'text-gray-500'
                    }`}>
                      {step === 1 && 'Informations'}
                      {step === 2 && 'Préférences'}
                      {step === 3 && 'Instructions'}
                    </span>
                  </div>
                  {step < 3 && (
                    <div className={`flex-1 h-1 mx-4 rounded transition-all ${
                      currentStep > step ? 'bg-primary-600' : 'bg-gray-200'
                    }`}></div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Step 1: User Information */}
        {currentStep === 1 && (
          <div className="bg-white rounded-2xl shadow-xl border border-primary-200 p-8 md:p-12">
            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <h2 className="text-3xl font-bold text-gray-900 mb-2">Bienvenue !</h2>
              <p className="text-gray-600">Commençons par quelques informations de base pour personnaliser votre expérience</p>
            </div>

            <form onSubmit={handleUserInfoSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Nom complet <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={userName}
                  onChange={(e) => setUserName(e.target.value)}
                  placeholder="Ex: Jean Dupont"
                  required
                  className="w-full px-4 py-3 border border-primary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all bg-white text-gray-900"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Âge <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="number"
                    value={userAge}
                    onChange={(e) => setUserAge(e.target.value)}
                    placeholder="Ex: 16"
                    min="10"
                    max="100"
                    required
                    className="w-full px-4 py-3 border border-primary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all bg-white text-gray-900"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Niveau académique <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={userAcademicLevel}
                    onChange={(e) => setUserAcademicLevel(e.target.value)}
                    required
                    className="w-full px-4 py-3 border border-primary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all bg-white text-gray-900"
                  >
                    <option value="collège">Collège</option>
                    <option value="lycée">Lycée</option>
                    <option value="université">Université</option>
                    <option value="professionnel">Professionnel</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email (optionnel)
                </label>
                <input
                  type="email"
                  value={userEmail}
                  onChange={(e) => setUserEmail(e.target.value)}
                  placeholder="Ex: jean.dupont@email.com"
                  className="w-full px-4 py-3 border border-primary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all bg-white text-gray-900"
                />
              </div>

              <button
                type="submit"
                className="w-full bg-gradient-to-r from-primary-600 to-primary-700 hover:from-primary-700 hover:to-primary-800 text-white font-semibold py-4 px-6 rounded-lg shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200 flex items-center justify-center"
              >
                Continuer
                <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </button>
            </form>
          </div>
        )}

        {/* Step 2: Quiz Preferences */}
        {currentStep === 2 && (
          <div className="bg-white rounded-2xl shadow-xl border border-primary-200 p-8 md:p-12">
            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                </svg>
              </div>
              <h2 className="text-3xl font-bold text-gray-900 mb-2">Préférences d'évaluation</h2>
              <p className="text-gray-600">Choisissez le domaine et le niveau pour personnaliser vos questions</p>
            </div>

            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Domaine d'étude <span className="text-red-500">*</span>
                </label>
                <select
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="w-full px-4 py-3 border border-primary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all bg-white text-gray-900"
                >
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
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Niveau de difficulté <span className="text-red-500">*</span>
                </label>
                <select
                  value={level}
                  onChange={(e) => setLevel(e.target.value)}
                  className="w-full px-4 py-3 border border-primary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all bg-white text-gray-900"
                >
                  <option value="collège">Collège (niveau débutant)</option>
                  <option value="lycée">Lycée (niveau intermédiaire)</option>
                  <option value="université">Université (niveau avancé)</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Informations complémentaires (optionnel)
                </label>
                <textarea
                  value={userInfo}
                  onChange={(e) => setUserInfo(e.target.value)}
                  placeholder="Ex: J'ai de bonnes bases en algèbre, mais je veux m'améliorer en géométrie..."
                  rows={4}
                  className="w-full px-4 py-3 border border-primary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all resize-none bg-white text-gray-900"
                />
                <p className="text-sm text-gray-500 mt-2">Ces informations nous aident à personnaliser vos questions</p>
              </div>

              <div className="flex space-x-4">
                <button
                  onClick={() => setCurrentStep(1)}
                  className="flex-1 bg-white hover:bg-gray-50 text-gray-700 font-semibold py-4 px-6 rounded-lg border-2 border-gray-300 transition-all duration-200"
                >
                  Retour
                </button>
                <button
                  onClick={handlePreferencesSubmit}
                  className="flex-1 bg-gradient-to-r from-primary-600 to-primary-700 hover:from-primary-700 hover:to-primary-800 text-white font-semibold py-4 px-6 rounded-lg shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200 flex items-center justify-center"
                >
                  Continuer
                  <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Instructions */}
        {currentStep === 3 && (
          <div className="bg-white rounded-2xl shadow-xl border border-primary-200 p-8 md:p-12">
            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h2 className="text-3xl font-bold text-gray-900 mb-2">Instructions importantes</h2>
              <p className="text-gray-600">Veuillez lire attentivement avant de commencer</p>
            </div>

            <div className="bg-amber-50 border-l-4 border-amber-500 p-6 rounded-r-lg mb-8">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-6 w-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-lg font-semibold text-amber-900 mb-2">Avertissement</h3>
                  <p className="text-amber-800">
                    Une fois le test commencé, vous ne pourrez plus l'arrêter avant la fin. Assurez-vous d'être prêt.
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-4 mb-8">
              <div className="flex items-start space-x-4">
                <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                  <svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900 mb-1">Durée du test</h4>
                  <p className="text-gray-600">Vous aurez exactement <strong>2 minutes</strong> pour répondre à la question. Un minuteur sera affiché.</p>
                </div>
              </div>

              <div className="flex items-start space-x-4">
                <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                  <svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                  </svg>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900 mb-1">Mode plein écran obligatoire</h4>
                  <p className="text-gray-600">Le test se déroulera en mode plein écran. Si vous quittez ce mode, le test sera automatiquement terminé.</p>
                </div>
              </div>

              <div className="flex items-start space-x-4">
                <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                  <svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900 mb-1">Niveau de confiance</h4>
                  <p className="text-gray-600">Après avoir répondu, vous devrez indiquer votre niveau de confiance dans votre réponse (0-100%).</p>
                </div>
              </div>

              <div className="flex items-start space-x-4">
                <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                  <svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                  </svg>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900 mb-1">Pas d'interruption</h4>
                  <p className="text-gray-600">Une fois commencé, vous ne pourrez pas mettre le test en pause ou revenir en arrière.</p>
                </div>
              </div>

              <div className="flex items-start space-x-4">
                <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                  <svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900 mb-1">Évaluation multimodale</h4>
                  <p className="text-gray-600">Votre performance, confiance et signaux non verbaux seront analysés pour une évaluation complète.</p>
                </div>
              </div>
            </div>

            <div className="bg-primary-50 border border-primary-200 rounded-lg p-6 mb-8">
              <h4 className="font-semibold text-primary-900 mb-2 flex items-center">
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Conseils
              </h4>
              <ul className="space-y-2 text-primary-800">
                <li className="flex items-start">
                  <span className="mr-2">•</span>
                  <span>Trouvez un endroit calme sans distractions</span>
                </li>
                <li className="flex items-start">
                  <span className="mr-2">•</span>
                  <span>Assurez-vous d'avoir une connexion internet stable</span>
                </li>
                <li className="flex items-start">
                  <span className="mr-2">•</span>
                  <span>Prenez le temps de bien lire la question</span>
                </li>
                <li className="flex items-start">
                  <span className="mr-2">•</span>
                  <span>Soyez honnête dans votre niveau de confiance</span>
                </li>
              </ul>
            </div>

            <div className="flex space-x-4">
              <button
                onClick={() => setCurrentStep(2)}
                className="flex-1 bg-white hover:bg-gray-50 text-gray-700 font-semibold py-4 px-6 rounded-lg border-2 border-gray-300 transition-all duration-200"
              >
                Retour
              </button>
              <button
                onClick={startTest}
                className="flex-1 bg-gradient-to-r from-primary-600 to-primary-700 hover:from-primary-700 hover:to-primary-800 text-white font-semibold py-4 px-6 rounded-lg shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200 flex items-center justify-center"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Commencer le test
              </button>
            </div>
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-primary-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-sm text-primary-600">
            © 2026 Projet SIMCO - Système Intelligent Multimodal d'Évaluation Cognitive
          </p>
        </div>
      </footer>
    </div>
  )
}

export default QuizPage
