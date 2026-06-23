const CATEGORIES = ['All', 'Dairy', 'Bakery', 'Fruit & Veg', 'Meat', 'Pantry', 'Drinks']

const SORT_OPTIONS = [
  { value: 'price_asc',  label: 'Lowest price' },
  { value: 'price_desc', label: 'Highest price' },
  { value: 'distance',   label: 'Closest store' },
  { value: 'relevance',  label: 'Best match' },
]

export default function FilterBar({ category, setCategory, sort, setSort }) {
  return (
    <div className="flex flex-wrap items-center gap-2 px-4 py-3
                    bg-white border-b border-gray-100">

      <span className="text-xs text-gray-400 mr-1">Category</span>

      {CATEGORIES.map(cat => (
        <button
          key={cat}
          onClick={() => setCategory(cat)}
          className={`px-3 py-1 rounded-full text-xs border transition-colors
            ${category === cat
              ? 'bg-brand-light text-brand-dark border-brand'
              : 'bg-white text-gray-500 border-gray-200 hover:border-gray-300'
            }`}
        >
          {cat}
        </button>
      ))}

      {/* Sort dropdown — pushed to the right */}
      <select
        value={sort}
        onChange={e => setSort(e.target.value)}
        className="ml-auto text-xs border border-gray-200 rounded-lg
                   px-2 py-1 text-gray-500 focus:outline-none"
      >
        {SORT_OPTIONS.map(opt => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </div>
  )
}