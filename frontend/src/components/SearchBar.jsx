import { useState } from 'react'
import { Search, MapPin } from 'lucide-react'

export default function SearchBar({ onSearch }) {
  const [postcode, setPostcode]       = useState('')
  const [productName, setProductName] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    if (!postcode || !productName) return
    onSearch({ postcode, productName })
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col sm:flex-row gap-2 p-4 bg-gray-50 border-b border-gray-100"
    >
      {/* Postcode input */}
      <div className="relative flex-shrink-0">
        <MapPin
          size={15}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
        />
        <input
          type="text"
          placeholder="Postcode"
          maxLength={4}
          value={postcode}
          onChange={e => setPostcode(e.target.value.replace(/\D/g, ''))}
          className="pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg
                     w-32 focus:outline-none focus:ring-2 focus:ring-brand/40"
        />
      </div>

      {/* Product name input */}
      <input
        type="text"
        placeholder="Product name, e.g. full cream milk"
        value={productName}
        onChange={e => setProductName(e.target.value)}
        className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg
                   focus:outline-none focus:ring-2 focus:ring-brand/40"
      />

      {/* Search button */}
      <button
        type="submit"
        className="flex items-center gap-2 px-5 py-2 bg-brand text-white
                   text-sm font-medium rounded-lg hover:bg-brand-dark
                   transition-colors"
      >
        <Search size={14} />
        Search
      </button>
    </form>
  )
}