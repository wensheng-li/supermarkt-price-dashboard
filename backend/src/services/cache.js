// Redis cache service
import { createClient } from "redis";

const client = createClient({
  url: process.env.REDIS_URL,
});

client.on("error", (err) => console.error("Redis Client Error", err));
client.on("connect", () => console.log("Connected to Redis"));

await client.connect();

export const cache = {
  // Get a cached value - returns parsed object or null if not found
  async get(key) {
    try {
      const value = await client.get(key);
      return value ? JSON.parse(value) : null;
    } catch (err) {
      console.error("Error getting cache", err);
      return null;
    }
  },

  // Set a value with TTL in seconds
  async set(key, value, ttl = process.env.CACHE_TTL ?? 300) {
    try {
      await client.setEx(key, Number(ttl), JSON.stringify(value));
    } catch (err) {
      console.error("Error setting cache", err);
    }
  },

  // Delete a cached entry
  async del(key) {
    try {
      await client.del(key);
    } catch (err) {
      console.error("Error deleting cache", err);
    }
  },

  // Clear all cache entries (use with caution)
  async clear() {
    try {
      await client.flushDb();
    } catch (err) {
      console.error("Error clearing cache", err);
    }
  },
};
