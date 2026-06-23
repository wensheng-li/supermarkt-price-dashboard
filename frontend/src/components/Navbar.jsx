import { ShoppingCart } from 'lucide-react'

export default function Navbar() {
  return (
    <nav className="bg-white border-b border-gray-100 px-6 py-3 flex items-center gap-3">
      <ShoppingCart size={20} className="text-brand" />
      <span className="font-medium text-gray-800">
        price<span className="text-brand">check</span>.au
      </span>
    </nav>
  )
}