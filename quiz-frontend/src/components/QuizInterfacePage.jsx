function QuizInterfacePage({
  subject,
  timeRemaining,
  formatTime,
  question,
  selectedOption,
  setSelectedOption,
  submitAnswer,
  loading = false,
  currentQuestion = 1,
  totalQuestions = 10,
}) {
  const normalizeOptionId = (rawId) => {
    const s = String(rawId ?? '').trim().toUpperCase();
    if (s === 'UN' || s === '1') return 'A';
    if (s === 'DEUX' || s === '2') return 'B';
    if (s === 'TROIS' || s === '3') return 'C';
    if (s === 'QUATRE' || s === '4') return 'D';
    if (['A', 'B', 'C', 'D'].includes(s)) return s;
    return s;
  };

  const handleOptionClick = (optionId) => {
    setSelectedOption(normalizeOptionId(optionId));
  };

  return (
    <div className="h-screen flex flex-col bg-gray-900">
      {/* Timer Bar */}
      <div className="bg-gradient-to-r from-primary-600 to-primary-700 px-4 sm:px-6 md:px-8 py-3 sm:py-4 flex justify-between items-center shadow-lg flex-wrap gap-2 sm:gap-0">
        <div className="flex items-center space-x-2 sm:space-x-4">
          <div className="w-8 h-8 sm:w-10 sm:h-10 bg-white/20 rounded-full flex items-center justify-center">
            <svg className="w-5 h-5 sm:w-6 sm:h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          <div className="text-white">
            <div className="text-sm sm:text-base md:text-lg font-semibold">{subject}</div>
            <div className="text-xs text-primary-100">Question {currentQuestion}/{totalQuestions}</div>
          </div>
        </div>

        <div className="flex items-center space-x-3 sm:space-x-6">
          {/* Progress Indicator */}
          <div className="text-white text-right hidden sm:block">
            <div className="text-xs text-primary-100 mb-1">PROGRESSION</div>
            <div className="flex items-center space-x-2">
              <div className="w-24 sm:w-32 h-2 bg-primary-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-white transition-all duration-300"
                  style={{ width: `${(currentQuestion / totalQuestions) * 100}%` }}
                ></div>
              </div>
              <span className="text-sm font-semibold">{Math.round((currentQuestion / totalQuestions) * 100)}%</span>
            </div>
          </div>

          <div className="w-px h-8 sm:h-12 bg-primary-500 hidden sm:block"></div>

          <div className={`flex items-center space-x-2 sm:space-x-6 ${timeRemaining <= 60 ? 'animate-pulse' : ''}`}>
            <div className="text-white text-right">
              <div className="text-xs text-primary-100 mb-1 hidden sm:block">TEMPS RESTANT</div>
              <div className={`text-xl sm:text-2xl md:text-3xl font-bold tracking-wider ${timeRemaining <= 60 ? 'text-red-300' : ''}`}>
                {formatTime(timeRemaining)}
              </div>
            </div>
            <svg className="w-8 h-8 sm:w-10 sm:h-10 md:w-12 md:h-12 text-white/80" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
      </div>

      {/* Main Quiz Content */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-0 overflow-hidden">
        {/* Left Side - Question */}
        <div className="bg-white p-4 sm:p-6 md:p-12 flex flex-col justify-center overflow-auto">
          <div className="max-w-2xl">
            <div className="flex items-center space-x-2 sm:space-x-3 mb-4 sm:mb-8">
              <div className="w-10 h-10 sm:w-12 sm:h-12 bg-primary-600 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 sm:w-7 sm:h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <h2 className="text-lg sm:text-xl md:text-2xl font-bold text-gray-900">Question</h2>
                <p className="text-xs sm:text-sm text-gray-500">Lisez attentivement et choisissez votre réponse</p>
              </div>
            </div>

            <div className="bg-primary-50 border-l-4 border-primary-600 p-4 sm:p-6 md:p-8 rounded-r-xl">
              <p className="text-base sm:text-lg md:text-xl text-gray-800 leading-relaxed whitespace-pre-line font-medium">
                {question?.question || "Chargement de la question..."}
              </p>
            </div>
          </div>
        </div>

        {/* Right Side - Answer Options */}
        <div className="bg-gradient-to-br from-gray-50 to-gray-100 p-4 sm:p-6 md:p-12 flex flex-col justify-center overflow-auto border-l-0 lg:border-l-4 border-primary-600">
          <div className="max-w-2xl">
            <div className="mb-4 sm:mb-8">
              <h2 className="text-lg sm:text-xl md:text-2xl font-bold text-gray-900 mb-2">Choisissez votre réponse</h2>
              <p className="text-xs sm:text-sm text-gray-600">Sélectionnez l'option qui vous semble correcte</p>
            </div>

            <div className="space-y-3 sm:space-y-4 mb-6 sm:mb-8">
              {question?.options?.map((option, idx) => {
                const displayId = ['A', 'B', 'C', 'D'][idx] || normalizeOptionId(option.id);
                const isSelected = normalizeOptionId(selectedOption) === displayId;
                const optionKey = `${question?.id ?? question?.question ?? 'q'}-${idx}-${String(option?.text ?? '')}`;
                return (
                <button
                  key={optionKey}
                  onClick={() => handleOptionClick(displayId)}
                  className={`w-full text-left p-3 sm:p-4 md:p-6 rounded-xl border-2 transition-all duration-200 transform hover:scale-[1.02] ${
                    isSelected
                      ? 'border-primary-600 bg-primary-50 shadow-lg'
                      : 'border-gray-300 bg-white hover:border-primary-400 hover:shadow-md'
                  }`}
                >
                  <div className="flex items-center space-x-3 sm:space-x-4">
                    <div className={`w-10 h-10 sm:w-12 sm:h-12 rounded-full flex items-center justify-center font-bold text-base sm:text-lg transition-colors ${
                      isSelected
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-200 text-gray-600'
                    }`}>
                      {displayId}
                    </div>
                    <div className="flex-1">
                      <p className={`text-sm sm:text-base md:text-lg font-medium ${
                        isSelected ? 'text-primary-900' : 'text-gray-800'
                      }`}>
                        {option.text}
                      </p>
                    </div>
                    {isSelected && (
                      <svg className="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                </button>
                );
              }) || (
                <div className="text-center text-gray-500">
                  <p>Chargement des options...</p>
                </div>
              )}
            </div>

            {/* Submit Button */}
            <button
              onClick={submitAnswer}
              disabled={selectedOption === null || loading}
              className="w-full bg-gradient-to-r from-primary-600 to-primary-700 hover:from-primary-700 hover:to-primary-800 disabled:from-gray-400 disabled:to-gray-500 text-white font-bold py-4 px-6 rounded-xl shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200 flex items-center justify-center"
            >
              {loading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Soumission en cours...
                </>
              ) : (
                <>
                  Soumettre la réponse
                  <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default QuizInterfacePage;
