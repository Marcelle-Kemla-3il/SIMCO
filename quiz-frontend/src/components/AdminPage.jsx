export default function AdminPage({ onBack }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-slate-100 p-4">
      <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-xl">
        <h1 className="text-2xl font-bold mb-4">Admin Page</h1>
        <p className="text-slate-600 mb-4">Page de gestion administrative (placeholder).</p>
        <button
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          onClick={onBack}
        >
          Retour
        </button>
      </div>
    </div>
  )
}
