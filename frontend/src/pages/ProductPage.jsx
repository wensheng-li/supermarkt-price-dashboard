import { useParams } from 'react-router-dom'

export default function ProductPage() {
  const { id } = useParams()

  return (
    <main className="max-w-2xl mx-auto px-4 py-10">
      <h1 className="text-lg font-medium text-gray-800 mb-2">Product detail</h1>
      <p className="text-sm text-gray-400">
        Product ID: <span className="font-mono">{id}</span>
      </p>
      <p className="text-sm text-gray-400 mt-4">
        Full price history and store comparison coming in a later step.
      </p>
    </main>
  )
}