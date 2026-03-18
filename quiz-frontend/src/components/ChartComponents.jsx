import { LineChart, Line, AreaChart, Area, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts'

export const KnowledgeCurveChart = ({ answers }) => {
  if (!answers || answers.length === 0) return null

  const data = answers.map((answer, idx) => ({
    questionIndex: `Q${idx + 1}`,
    correct: answer.isCorrect ? 1 : 0,
    correctPct: Math.round((answers.slice(0, idx + 1).filter(a => a.isCorrect).length / (idx + 1)) * 100)
  }))

  const score = answers.length > 0 ? Math.round((answers.filter(a => a.isCorrect).length / answers.length) * 100) : 0

  return (
    <div className="w-full">
      <div className="mb-4">
        <h3 className="text-lg font-bold text-gray-800 mb-2">Courbe de Connaissance</h3>
        <p className="text-sm text-gray-600 mb-4">Score final: <span className="font-bold text-primary-600">{score}%</span></p>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={data} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
          <defs>
            <linearGradient id="colorPct" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#22c55e" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#22c55e" stopOpacity={0.1} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="questionIndex" stroke="#6b7280" />
          <YAxis stroke="#6b7280" domain={[0, 100]} />
          <Tooltip
            contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px' }}
            formatter={(value) => `${value}%`}
          />
          <Area type="monotone" dataKey="correctPct" stroke="#22c55e" fillOpacity={1} fill="url(#colorPct)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

export const ConfidenceProgressionChart = ({ answers, emotionHistory }) => {
  if (!answers || answers.length === 0) return null

  const data = answers.map((answer, idx) => {
    const emotions = emotionHistory[idx] || {}
    const observedConf = emotions.confidence_score !== undefined ? Math.round(emotions.confidence_score * 100) : 50

    return {
      questionIndex: `Q${idx + 1}`,
      declared: answer.confidence_declared !== undefined ? Math.round(answer.confidence_declared * 100) : 50,
      observed: observedConf,
      correct: answer.isCorrect ? 1 : 0
    }
  })

  return (
    <div className="w-full">
      <div className="mb-4">
        <h3 className="text-lg font-bold text-gray-800 mb-2">Progression de la Confiance</h3>
        <p className="text-sm text-gray-600">Confiance déclarée vs observée (via émotions)</p>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={data} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
          <defs>
            <linearGradient id="colorDeclared" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1} />
            </linearGradient>
            <linearGradient id="colorObserved" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.1} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="questionIndex" stroke="#6b7280" />
          <YAxis stroke="#6b7280" domain={[0, 100]} />
          <Tooltip
            contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px' }}
            formatter={(value) => `${value}%`}
          />
          <Legend />
          <Area type="monotone" dataKey="declared" stroke="#3b82f6" fillOpacity={1} fill="url(#colorDeclared)" name="Déclarée" />
          <Area type="monotone" dataKey="observed" stroke="#f59e0b" fillOpacity={1} fill="url(#colorObserved)" name="Observée" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

export const EmotionRadarChart = ({ emotionHistory }) => {
  if (!emotionHistory || emotionHistory.length === 0) return null

  const emotions = ["happy", "neutral", "sad", "angry", "fear", "surprise", "disgust"]
  const aggregated = {}

  emotions.forEach(e => {
    const counts = emotionHistory.filter(eh => eh.dominant_emotion === e).length
    aggregated[e] = Math.round((counts / emotionHistory.length) * 100)
  })

  const data = emotions.map(e => ({
    emotion: e.charAt(0).toUpperCase() + e.slice(1),
    value: aggregated[e],
    fullMark: 100
  }))

  return (
    <div className="w-full">
      <div className="mb-4">
        <h3 className="text-lg font-bold text-gray-800 mb-2">Répartition des Émotions</h3>
        <p className="text-sm text-gray-600">Distribution des émotions détectées</p>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <RadarChart data={data}>
          <PolarGrid stroke="#d1d5db" />
          <PolarAngleAxis dataKey="emotion" stroke="#6b7280" />
          <PolarRadiusAxis angle={90} domain={[0, 100]} stroke="#9ca3af" />
          <Radar name="Fréquence (%)" dataKey="value" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.6} />
          <Tooltip
            contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px' }}
            formatter={(value) => `${value}%`}
          />
          <Legend />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}

export const CorrectAnswerRateChart = ({ answers }) => {
  if (!answers || answers.length === 0) return null

  const total = answers.length
  const correct = answers.filter(a => a.isCorrect).length
  const incorrect = total - correct

  const data = [
    { name: 'Correctes', value: correct, fill: '#22c55e' },
    { name: 'Incorrectes', value: incorrect, fill: '#ef4444' }
  ]

  return (
    <div className="w-full">
      <div className="mb-4">
        <h3 className="text-lg font-bold text-gray-800 mb-2">Taux de Réussite</h3>
        <p className="text-sm text-gray-600">{correct} / {total} réponses correctes</p>
      </div>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="name" stroke="#6b7280" />
          <YAxis stroke="#6b7280" />
          <Tooltip
            contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px' }}
          />
          <Bar dataKey="value" fill="#8b5cf6" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export const EmotionTimeSeriesChart = ({ emotionHistory }) => {
  if (!emotionHistory || emotionHistory.length === 0) return null

  const emotions = ["happy", "neutral", "sad", "angry", "fear", "surprise", "disgust"]
  const colors = {
    happy: '#fbbf24',
    neutral: '#9ca3af',
    sad: '#ef4444',
    angry: '#dc2626',
    fear: '#7c3aed',
    surprise: '#06b6d4',
    disgust: '#10b981'
  }

  const data = emotionHistory.map((eh, idx) => ({
    questionIndex: `Q${idx + 1}`,
    ...emotions.reduce((acc, e) => {
      acc[e] = (eh.emotions?.[e] || 0) * 100
      return acc
    }, {})
  }))

  return (
    <div className="w-full">
      <div className="mb-4">
        <h3 className="text-lg font-bold text-gray-800 mb-2">Évolution Temporelle des Émotions</h3>
        <p className="text-sm text-gray-600">Probabilités d'émotions au fil de l'examen</p>
      </div>
      <ResponsiveContainer width="100%" height={350}>
        <AreaChart data={data} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="questionIndex" stroke="#6b7280" />
          <YAxis stroke="#6b7280" domain={[0, 100]} />
          <Tooltip
            contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px' }}
            formatter={(value) => `${Math.round(value)}%`}
          />
          <Legend />
          {emotions.map((e, idx) => (
            <Area
              key={e}
              type="monotone"
              dataKey={e}
              stroke={colors[e]}
              fill={colors[e]}
              fillOpacity={0.3}
              stackId="emotions"
              name={e.charAt(0).toUpperCase() + e.slice(1)}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}