import { useState } from 'react'
import SearchBar   from '../components/SearchBar'
import FilterBar   from '../components/FilterBar'
import ProductCard from '../components/ProductCard'
import { useProducts } from '../hooks/useProducts'

export default function SearchPage() {
  const [query,    setQuery]    = useState({ postcode: '', productName: '' })
  const [category, setCategory] = useState('All')
  const [sort,     setSort]     = useState('price_asc')

  const { data, isLoading, isError } = useProducts({
    ...query,
    category: category === 'All' ? undefined : category,
    sort,
  })

  return (
    <>
      <SearchBar onSearch={setQuery} />
      <FilterBar
        category={category} setCategory={setCategory}
        sort={sort}         setSort={setSort}
      />

      <main className="max-w-4xl mx-auto px-4 py-6">

        {/* Loading state */}
        {isLoading && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-40 bg-gray-100 rounded-xl animate-pulse" />
            ))}
          </div>
        )}

        {/* Error state */}
        {isError && (
          <p className="text-center text-red-500 mt-10">
            Could not load results. Is the backend running?
          </p>
        )}

        {/* Results grid */}
        {data?.products && (
          <>
            <p className="text-xs text-gray-400 mb-3">
              {data.products.length} results near {query.postcode}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {data.products.map(product => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          </>
        )}

        {/* Empty state */}
        {!isLoading && data?.products?.length === 0 && (
          <p className="text-center text-gray-400 mt-16 text-sm">
            No products found. Try a different search.
          </p>
        )}

        {/* Prompt to search */}
        {!query.productName && (
          <p className="text-center text-gray-400 mt-16 text-sm">
            Enter a postcode and product above to compare prices.
          </p>
        )}
      </main>
    </>
  )
}