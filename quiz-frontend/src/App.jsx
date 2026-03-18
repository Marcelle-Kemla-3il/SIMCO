import { useState } from 'react'
import './App.css'
import LandingPage from './components/LandingPage'
import QuizPage from './components/QuizPage'
import AdminPage from './components/AdminPage'
import ErrorBoundary from './components/ErrorBoundary'

function App() {
  const [showQuiz, setShowQuiz] = useState(false)

  const hash = typeof window !== 'undefined' ? String(window.location.hash || '') : ''
  const isAdmin = hash === '#/admin'

  return (
    <ErrorBoundary>
      {isAdmin ? (
        <AdminPage onBack={() => { window.location.hash = '' }} />
      ) : showQuiz ? (
        <QuizPage onBackToHome={() => setShowQuiz(false)} />
      ) : (
        <LandingPage onStart={() => setShowQuiz(true)} />
      )}
    </ErrorBoundary>
  )
}

export default App
