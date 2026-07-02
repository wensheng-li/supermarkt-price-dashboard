import { prisma } from "../db/prisma.js";
import { cache } from "../services/cache.js";
import { getNearestStores } from "../services/postcode.js";
import { runScraper } from "../services/scraper.js";
import {
  cancelScraperJob,
  getScraperJobStatus,
} from "../services/scraperQueue.js";

const ACTIVE_SCRAPE_STATES = [
  "active",
  "waiting",
  "started",
  "in_progress",
  "delayed",
  "cancelling",
];

function buildJobCacheKey(postcode, productName, state, category) {
  const normalizedQuery = `${postcode}:${state ?? ""}:${productName}`
    .toLowerCase()
    .replace(/\s+/g, "_");
  return `scrapeJob:${normalizedQuery}:${category ?? "all"}`;
}

export async function searchProducts(req, res, next) {
  try {
    const {
      postcode,
      state,
      productName,
      category,
      sort = "price_asc",
      restart = "false",
    } = req.query;

    if (!postcode || !productName) {
      return res.status(400).json({
        error: "postcode and productName are required",
      });
    }

    const cacheKey = `search:${postcode}:${state}:${productName}:${category ?? "all"}:${sort}`;

    // 1. Check Redis cache first
    const cached = await cache.get(cacheKey);
    if (cached) {
      console.log(`[search] Cache hit for "${productName}" @ ${postcode}`);
      return res.json({ ...cached, fromCache: true });
    }

    // 2. Get nearest stores for this postcode & state
    const nearestStores = await getNearestStores(postcode, state);
    let storeIds = nearestStores.map((s) => s.id);
    const EMPTY_RESULT_TTL = 120; // 2  minutes

    // 3. Check if database has products matching this query
    let products = await queryProducts(productName, storeIds, category);

    // 4. If no results, check for an existing scrape job before enqueuing
    if (!products.length) {
      const emptyMarkerKey = `empty:${cacheKey}`;
      const alreadyTriedAndEmpty = await cache.get(emptyMarkerKey);

      if (alreadyTriedAndEmpty) {
        console.log(
          `[search] Already scraped "${productName}" @ ${postcode} — no data available`,
        );
        return res.json({
          products: [],
          scraped: true,
          reason: "no_data_available",
        });
      }

      const jobCacheKey = buildJobCacheKey(
        postcode,
        productName,
        state,
        category,
      );
      const existingJob = await cache.get(jobCacheKey);
      const shouldRestartScrape = restart === "true";

      if (existingJob?.jobId) {
        const existingStatus = await getScraperJobStatus(existingJob.jobId);
        if (
          existingStatus &&
          ACTIVE_SCRAPE_STATES.includes(existingStatus.state)
        ) {
          if (shouldRestartScrape) {
            console.log(
              `[search] Restart requested — cancelling scrape job ${existingJob.jobId}`,
            );
            await cancelScraperJob(existingJob.jobId);
            await cache.del(jobCacheKey);
          } else {
            console.log(
              `[search] Existing scrape job in progress for "${productName}" @ ${postcode}: ${existingJob.jobId}`,
            );
            return res.json({ status: "scraping", jobId: existingJob.jobId });
          }
        } else {
          await cache.del(jobCacheKey);
        }
      }

      const latestExistingJob = shouldRestartScrape
        ? null
        : await cache.get(jobCacheKey);

      if (latestExistingJob?.jobId) {
        const existingStatus = await getScraperJobStatus(
          latestExistingJob.jobId,
        );
        if (
          existingStatus &&
          ACTIVE_SCRAPE_STATES.includes(existingStatus.state)
        ) {
          console.log(
            `[search] Existing scrape job in progress for "${productName}" @ ${postcode}: ${latestExistingJob.jobId}`,
          );
          return res.json({
            status: "scraping",
            jobId: latestExistingJob.jobId,
          });
        }
        await cache.del(jobCacheKey);
      }

      console.log(
        `[search] No results found — enqueueing scraper for "${productName}"`,
      );

      try {
        const job = await runScraper(productName, postcode, state);
        await cache.set(
          jobCacheKey,
          { jobId: job.id, status: "running" },
          60 * 10,
        );
        return res.json({ status: "scraping", jobId: job.id });
      } catch (scraperErr) {
        console.error(
          "[search] Failed to enqueue scraper:",
          scraperErr.message,
        );
        // Fallthrough to return empty result
      }
    }

    // 5. Shape the response
    const shaped = shapeProducts(products, nearestStores, sort);
    const result = { products: shaped };

    // 6. Cache the result
    // Only cache if we actually have results
    if (shaped.length > 0) {
      await cache.set(cacheKey, result);
    } else {
      // Mark this exact query as "tried and empty" so it doesn't
      // immediately re-trigger another scrap loop
      await cache.set(`empty:${cacheKey}`, true, EMPTY_RESULT_TTL);
    }

    return res.json(result);
  } catch (err) {
    next(err);
  }
}

// ─── Helpers ────────────────────────────────────────────────────────────────

async function queryProducts(productName, storeIds, category) {
  if (!storeIds.length) return [];

  return prisma.product.findMany({
    where: {
      name: { contains: productName, mode: "insensitive" },
      ...(category && category !== "All" && { category }),
      prices: { some: { storeId: { in: storeIds } } },
    },
    include: {
      prices: {
        where: { storeId: { in: storeIds } },
        orderBy: { scrapedAt: "desc" },
        distinct: ["storeId"],
        include: { store: true },
      },
    },
  });
}

function shapeProducts(products, nearestStores, sort) {
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

  return sortProducts(shaped, sort);
}

function sortStores(stores, sort) {
  if (sort === "price_asc")
    return [...stores].sort((a, b) => a.price - b.price);
  if (sort === "price_desc")
    return [...stores].sort((a, b) => b.price - a.price);
  if (sort === "distance")
    return [...stores].sort((a, b) => a.distance - b.distance);
  return stores;
}

function sortProducts(products, sort) {
  if (sort === "price_asc")
    return [...products].sort(
      (a, b) => a.stores[0]?.price - b.stores[0]?.price,
    );
  if (sort === "price_desc")
    return [...products].sort(
      (a, b) => b.stores[0]?.price - a.stores[0]?.price,
    );
  if (sort === "distance")
    return [...products].sort(
      (a, b) => a.nearestStore?.distance - b.nearestStore?.distance,
    );
  return products;
}
