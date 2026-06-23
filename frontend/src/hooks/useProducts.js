/**
 * React Query fetches data from the backend
 */
import { useQuery } from "@tanstack/react-query";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:3001";

export function useProducts({ postcode, productName, category, sort }) {
  return useQuery({
    // Cache key — refetches automatically when any param changes
    queryKey: ["products", postcode, productName, category, sort],

    queryFn: async () => {
      const { data } = await axios.get(`${API_BASE}/api/products/search`, {
        params: { postcode, productName, category, sort },
      });
      return data;
    },

    // Only fetch when we have both a postcode and a product name
    enabled: Boolean(postcode && productName),
  });
}
