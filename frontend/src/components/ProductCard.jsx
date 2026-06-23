import { MapPin } from 'lucide-react'

// Colour dot per store chain
const STORE_COLOURS = {
  woolworths: 'bg-woolworths',
  coles:      'bg-coles',
  iga:        'bg-iga',
}

export default function ProductCard({ product }) {
  // Sort stores cheapest first
  const stores = [...product.stores].sort((a, b) => a.price - b.price)
  const bestPrice = stores[0]?.price

  return (
    <div className="bg-white border border-gray-100 rounded-xl p-4
                    hover:border-brand/40 transition-colors">

      {/* Header row */}
      <div className="flex justify-between items-start mb-3 gap-2">
        <h3 className="text-sm font-medium text-gray-800 leading-snug">
          {product.name}
        </h3>
        <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5
                         rounded-full whitespace-nowrap flex-shrink-0">
          {product.category}
        </span>
      </div>

      {/* Store price rows */}
      <div className="flex flex-col gap-1.5">
        {stores.map(store => (
          <div
            key={store.name}
            className="flex justify-between items-center
                       bg-gray-50 rounded-lg px-3 py-1.5"
          >
            {/* Store name + coloured dot */}
            <div className="flex items-center gap-2">
              <span
                className={`w-2 h-2 rounded-full flex-shrink-0
                  ${STORE_COLOURS[store.name.toLowerCase()] ?? 'bg-gray-400'}`}
              />
              <span className="text-xs text-gray-500">{store.name}</span>
            </div>

            {/* Price — green if best */}
            <div className="flex items-center gap-1.5">
              <span
                className={`text-sm font-medium
                  ${store.price === bestPrice ? 'text-brand-dark' : 'text-gray-700'}`}
              >
                ${store.price.toFixed(2)}
              </span>
              {store.price === bestPrice && (
                <span className="text-[10px] bg-brand-light text-brand-dark
                                 px-1.5 py-0.5 rounded">
                  best
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Distance note */}
      {product.nearestStore && (
        <p className="text-[11px] text-gray-400 mt-2 flex items-center gap-1">
          <MapPin size={10} />
          Nearest: {product.nearestStore.name} — {product.nearestStore.distance}km
        </p>
      )}
    </div>
  )
}