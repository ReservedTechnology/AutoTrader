export default function HomePage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            {{PROJECT_NAME}}
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Proyecto Next.js creado exitosamente
          </p>
          <div className="bg-white rounded-lg shadow-lg p-8 max-w-md mx-auto">
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">
              ¡Bienvenido!
            </h2>
            <p className="text-gray-600 mb-6">
              Tu proyecto está listo para comenzar a desarrollar.
            </p>
            <button className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors">
              Comenzar
            </button>
          </div>
        </div>
      </div>
    </main>
  )
}
