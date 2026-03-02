import { useState } from 'react'
import './App.css'
import LandingPage from './components/LandingPage'
import QuizPage from './components/QuizPage'

function App() {
  const [showQuiz, setShowQuiz] = useState(false)

  return (
    <>
      {showQuiz ? (
        <QuizPage onBackToHome={() => setShowQuiz(false)} />
      ) : (
        <LandingPage onStart={() => setShowQuiz(true)} />
      )}
    </>
  )
}

export default App
