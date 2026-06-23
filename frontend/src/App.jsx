import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import SearchPage from './pages/SearchPage'
import ProductPage from './pages/ProductPage'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <Routes>
        <Route path="/"           element={<SearchPage />} />
        <Route path="/product/:id" element={<ProductPage />} />
      </Routes>
    </div>
  )
}