/**
 * Product Search Controller
 *
 * This controller handles the core product search functionality.
 * It checks the Redis cache for results first, then queries the database if needed.
 */
import { prisma } from "../db/prisma.js";
import { getNearestStores } from "../services/postcode.js";
import { cache } from "../services/cache.js";

export async function searchProducts(req, res, next) {
  try {
    const { postcode, productName, category, sort = "price_asc" } = req.query;

    if (!postcode || !productName) {
      return res
        .status(400)
        .json({ error: "postcode and productName are required" });
    }

    // Build a cache key from all search params
    const cacheKey = `search:${postcode}:${productName}:${category ?? "all"}:${sort}`;

    // Check Redis cache first
    const cached = await cache.get(cacheKey);
    if (cached) {
      return res.json({ ...cached, fromCache: true });
    }

    // Get nearest stores for this postcode
    const nearestStores = await getNearestStores(postcode);
    const storeIds = nearestStores.map((s) => s.id);

    if (!storeIds.length) {
      return res.json({
        products: [],
        message: "No stores found near this postcode",
      });
    }

    // Build the Prisma query
    const products = await prisma.product.findMany({
      where: {
        // Fuzzy name match — case insensitive contains
        name: { contains: productName, mode: "insensitive" },

        // Optional category filter
        ...(category && category !== "All" && { category }),

        // Only include products that have prices at nearby stores
        prices: { some: { storeId: { in: storeIds } } },
      },
      include: {
        prices: {
          where: { storeId: { in: storeIds } },
          orderBy: { scrapedAt: "desc" },
          // Only the most recent price per store
          distinct: ["storeId"],
          include: { store: true },
        },
      },
    });

    // Shape the response
    const shaped = products.map((product) => {
      const stores = product.prices.map((p) => ({
        name: p.store.name,
        chain: p.store.chain,
        price: p.price,
        wasPrice: p.wasPrice,
        isOnSale: p.isOnSale,
        address: p.store.address,
        distance: nearestStores.find((s) => s.id === p.storeId)?.distance,
      }));

      // Sort stores by chosen sort method
      const sorted = sortStores(stores, sort);

      return {
        id: product.id,
        name: product.name,
        brand: product.brand,
        category: product.category,
        unit: product.unit,
        imageUrl: product.imageUrl,
        stores: sorted,
        nearestStore: sorted[0] ?? null,
      };
    });

    // Sort the product list itself
    const result = { products: sortProducts(shaped, sort) };

    // Save to Redis for next request
    await cache.set(cacheKey, result);

    return res.json(result);
  } catch (err) {
    next(err);
  }
}

function sortStores(stores, sort) {
  if (sort === "price_asc") return stores.sort((a, b) => a.price - b.price);
  if (sort === "price_desc") return stores.sort((a, b) => b.price - a.price);
  if (sort === "distance")
    return stores.sort((a, b) => a.distance - b.distance);
  return stores;
}

function sortProducts(products, sort) {
  if (sort === "price_asc")
    return products.sort((a, b) => a.stores[0]?.price - b.stores[0]?.price);
  if (sort === "price_desc")
    return products.sort((a, b) => b.stores[0]?.price - a.stores[0]?.price);
  if (sort === "distance")
    return products.sort(
      (a, b) => a.nearestStore?.distance - b.nearestStore?.distance,
    );
  return products;
}
