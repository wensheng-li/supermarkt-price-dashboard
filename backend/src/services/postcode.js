/**
 * Postcode lookup service
 *
 * This converts a postcode into coordinates, then finds the nearest stores
 */
import axios from "axios";
import { prisma } from "../db/prisma.js";

// Full state name map — Nominatim understands full names better than abbreviations
const STATE_FULL_NAMES = {
  NSW: "New South Wales",
  VIC: "Victoria",
  QLD: "Queensland",
  SA: "South Australia",
  WA: "Western Australia",
  TAS: "Tasmania",
  ACT: "Australian Capital Territory",
  NT: "Northern Territory",
};

// Convert postcode → { lat, lon } using free Nominatim API (no key needed)
export async function getCoordinatesFromPostcode(postcode, state = "") {
  const url = "https://nominatim.openstreetmap.org/search";

  // Build the query — more specific = more accurate
  // e.g. "5161, South Australia, Australia" instead of just "5161"
  const stateFull = STATE_FULL_NAMES[state?.toUpperCase()] ?? "";
  const queryParts = [postcode, stateFull, "Australia"].filter(Boolean);
  const queryStr = queryParts.join(", ");

  const { data } = await axios.get(url, {
    params: {
      q: queryStr, // free-form query — more reliable than postalcode param
      format: "json",
      limit: 5, // fetch top 5 so we can pick the best match
      countrycodes: "au", // restrict to Australia at API level
    },
    headers: {
      "User-Agent": "supermarket-price-dashboard/1.0",
    },
  });

  if (!data.length) return null;

  // If state was provided, find the result that matches it
  if (stateFull) {
    const match = data.find(
      (result) =>
        result.display_name?.includes(stateFull) ||
        result.display_name?.includes(state),
    );
    if (match) {
      return {
        lat: parseFloat(match.lat),
        lon: parseFloat(match.lon),
        displayName: match.display_name,
      };
    }
  }

  // Fallback — prefer results with 'suburb' or 'postcode' type
  // over less specific results like 'county' or 'state'
  const preferred = data.find((r) =>
    ["suburb", "postcode", "residential", "village", "town", "city"].includes(
      r.type,
    ),
  );

  const best = preferred ?? data[0];

  return {
    lat: parseFloat(best.lat),
    lon: parseFloat(best.lon),
    displayName: best.display_name,
  };
}

// Find stores within ~10km using simple coordinate bounding box
// (Good enough for MVP — swap for PostGIS query later for precision)
export async function getNearestStores(postcode, state = "", radiusKm = 10) {
  const coords = await getCoordinatesFromPostcode(postcode, state);
  if (!coords) return [];

  console.log(`[postcode] ${postcode} ${state} → ${coords.displayName}`);
  console.log(`[postcode] Coordinates: ${coords.lat}, ${coords.lon}`);

  // 1 degree latitude ≈ 111km, so radiusKm/111 gives degree offset
  const delta = radiusKm / 111;

  // ← Add this block
  console.log(`[postcode] Bounding box:`, {
    latMin: coords.lat - delta,
    latMax: coords.lat + delta,
    lonMin: coords.lon - delta,
    lonMax: coords.lon + delta,
  });

  const stores = await prisma.store.findMany({
    where: {
      latitude: { gte: coords.lat - delta, lte: coords.lat + delta },
      longitude: { gte: coords.lon - delta, lte: coords.lon + delta },
    },
  });
  // console.log(`[postcode] Found ${stores.length} stores within ${radiusKm}km`);
  console.log(`[postcode] Total stores in DB: ${stores.length}`);
  stores.forEach((s) => {
    console.log(
      `[postcode]   ${s.name} lat=${s.latitude} lon=${s.longitude} ` +
        `→ inBox=${
          s.latitude >= coords.lat - delta &&
          s.latitude <= coords.lat + delta &&
          s.longitude >= coords.lon - delta &&
          s.longitude <= coords.lon + delta
        }`,
    );
  });
  // Calculate actual distance and sort nearest first
  return stores
    .map((store) => ({
      ...store,
      distance: getDistanceKm(
        coords.lat,
        coords.lon,
        store.latitude,
        store.longitude,
      ),
    }))
    .sort((a, b) => a.distance - b.distance);
}

// Haversine formula — straight-line distance between two coordinates
function getDistanceKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return +(R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))).toFixed(1);
}

function toRad(deg) {
  return deg * (Math.PI / 180);
}
