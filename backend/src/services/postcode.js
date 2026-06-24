/**
 * Postcode lookup service
 *
 * This converts a postcode into coordinates, then finds the nearest stores
 */
import axios from "axios";
import { prisma } from "../db/prisma.js";

// Convert postcode → { lat, lon } using free Nominatim API (no key needed)
export async function getCoordinatesFromPostcode(postcode) {
  const url = "https://nominatim.openstreetmap.org/search";

  const { data } = await axios.get(url, {
    params: {
      postalcode: postcode,
      country: "Australia",
      format: "json",
      limit: 1,
    },
    headers: {
      // Nominatim requires a User-Agent identifying your app
      "User-Agent": "supermarket-price-dashboard/1.0",
    },
  });

  if (!data.length) return null;

  return {
    lat: parseFloat(data[0].lat),
    lon: parseFloat(data[0].lon),
  };
}

// Find stores within ~10km using simple coordinate bounding box
// (Good enough for MVP — swap for PostGIS query later for precision)
export async function getNearestStores(postcode, radiusKm = 10) {
  const coords = await getCoordinatesFromPostcode(postcode);
  if (!coords) return [];

  // 1 degree latitude ≈ 111km, so radiusKm/111 gives degree offset
  const delta = radiusKm / 111;

  const stores = await prisma.store.findMany({
    where: {
      latitude: { gte: coords.lat - delta, lte: coords.lat + delta },
      longitude: { gte: coords.lon - delta, lte: coords.lon + delta },
    },
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
