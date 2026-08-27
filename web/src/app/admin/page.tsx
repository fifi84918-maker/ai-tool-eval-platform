export default function AdminPage() {
  const stats = [
    { name: 'Total Skills', value: '—', color: 'bg-blue-500' },
    { name: 'Pending Reviews', value: '—', color: 'bg-yellow-500' },
    { name: 'Approved Skills', value: '—', color: 'bg-green-500' },
    { name: 'Failed Tests', value: '—', color: 'bg-red-500' },
  ]

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow">
        <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
        <p className="mt-2 text-gray-600">
          Coming in Phase 2: Full administrative interface for skill management,
          review workflows, and benchmarking configuration.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
          <div key={stat.name} className="bg-white p-6 rounded-lg shadow">
            <div className={`w-12 h-12 ${stat.color} rounded-lg mb-4`}></div>
            <h3 className="text-sm font-medium text-gray-500">{stat.name}</h3>
            <p className="text-3xl font-bold text-gray-900 mt-2">{stat.value}</p>
          </div>
        ))}
      </div>

      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-lg font-semibold mb-4">Upcoming Features</h2>
        <ul className="space-y-2 text-gray-700">
          <li>• Manual skill approval/rejection workflow</li>
          <li>• Benchmark test case management</li>
          <li>• Evidence storage and retrieval (MinIO integration)</li>
          <li>• LLM judge configuration and fallback pool</li>
          <li>• Real-time evaluation job monitoring</li>
          <li>• Cost tracking and budget limits</li>
        </ul>
      </div>
    </div>
  )
}
