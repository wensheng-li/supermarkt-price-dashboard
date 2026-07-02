/**
 * Runs the Python scraper as a child process, passing the product query as an argument.
 */
import { randomUUID } from "crypto";
import scraperQueue from "./scraperQueue.js";

// Enqueue a scraping job. Returns the Bull job object.
export async function runScraper(productQuery, postcode, state) {
  console.log(
    `[scraper] Enqueueing scrape for: "${productQuery}" @ ${postcode} ${state ?? ""}`,
  );
  const job = await scraperQueue.add(
    { productName: productQuery, postcode, state },
    {
      jobId: `scrape-${Date.now()}-${randomUUID()}`,
      removeOnComplete: true,
      removeOnFail: false,
    },
  );
  return job;
}
