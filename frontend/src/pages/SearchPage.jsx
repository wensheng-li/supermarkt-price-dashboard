import { useState } from 'react'
import { Square } from 'lucide-react'
import SearchBar   from '../components/SearchBar'
import FilterBar   from '../components/FilterBar'
import ProductCard from '../components/ProductCard'
import { useProducts } from '../hooks/useProducts'

export default function SearchPage() {
  const [query,    setQuery]    = useState({
    postcode: '',
    state: '',
    productName: '',
    runId: null,
  })
  const [category, setCategory] = useState('All')
  const [sort,     setSort]     = useState('price_asc')

  const {
    data,
    isLoading,
    isError,
    jobId,
    jobProgress,
    jobState,
    isStopping,
    stopScraping,
  } = useProducts({
    ...query,
    category: category === 'All' ? undefined : category,
    sort,
  })

  function handleSearch(nextQuery) {
    setQuery({
      ...nextQuery,
      runId: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    })
  }

  return (
    <>
      {/* onSearch now receives { postcode, state, productName } */}
      <SearchBar onSearch={handleSearch} />

      <FilterBar
        category={category} setCategory={setCategory}
        sort={sort}         setSort={setSort}
      />

      <main className="max-w-4xl mx-auto px-4 py-6">

        {/* Loading state */}
        {isLoading && (
          <div className="flex flex-col items-center gap-3 mt-16 text-gray-400">
            <div className="w-6 h-6 border-2 border-brand border-t-transparent
                            rounded-full animate-spin" />
            <p className="text-sm">
              Fetching prices for <span className="font-medium text-gray-600">
                {query.productName}
              </span> near <span className="font-medium text-gray-600">
                {query.postcode}
              </span>...
            </p>
            <p className="text-xs text-gray-300">
              First search may take 15–20 seconds while we fetch fresh data
            </p>
            {/* Job progress indicator */}
            {jobId && (
              <ScrapeProgress
                jobId={jobId}
                jobProgress={jobProgress}
                jobState={jobState}
                isStopping={isStopping}
                onStop={stopScraping}
              />
            )}
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

        {/* Scraping in-progress (backend enqueued job) */}
        {!isLoading && data?.status === "scraping" && jobId && (
          <div className="flex flex-col items-center gap-3 mt-8 text-gray-500">
            <div className="text-sm">
              {jobState === 'cancelling'
                ? 'Stopping scrape...'
                : 'Fetching fresh data — scraping in progress'}
            </div>
            <ScrapeProgress
              jobId={jobId}
              jobProgress={jobProgress}
              jobState={jobState}
              isStopping={isStopping}
              onStop={stopScraping}
            />
          </div>
        )}

        {!isLoading && data?.reason === 'no_data_available' && (
          <p className="text-center text-gray-400 mt-16 text-sm">
            No stores found near {query.postcode}. Try a postcode closer to a major city.
          </p>
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

function ScrapeProgress({ jobId, jobProgress, jobState, isStopping, onStop }) {
  const progress = Math.min(100, Math.max(0, jobProgress ?? 0))
  const stopping = isStopping || jobState === 'cancelling'

  return (
    <div className="w-full max-w-md mt-3">
      <div className="text-xs text-gray-500 mb-1 break-all">
        Scraping job: <span className="font-mono">{jobId}</span>
      </div>
      <div className="w-full bg-gray-200 rounded h-2 overflow-hidden">
        <div className="h-2 bg-brand" style={{ width: `${progress}%` }} />
      </div>
      <div className="flex items-center justify-between gap-3 mt-2">
        <div className="text-xs text-gray-400">{progress}%</div>
        <button
          type="button"
          onClick={onStop}
          disabled={stopping}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium
                     text-red-600 border border-red-200 rounded-lg bg-white
                     hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Square size={11} />
          {stopping ? 'Stopping' : 'Stop'}
        </button>
      </div>
    </div>
  )
}
