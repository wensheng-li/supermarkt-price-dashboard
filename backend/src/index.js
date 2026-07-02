/**
 * The main server entry
 */

import "dotenv/config";
import express from "express";
import cors from "cors";
import helmet from "helmet";
import rateLimit from "express-rate-limit";
import productRoutes from "./routes/products.js";
import scraperRoutes from "./routes/scraper.js";
import { errorHandler } from "./middleware/errorHandler.js";

const app = express();
const PORT = process.env.PORT ?? 3001;

// Security headers
app.use(helmet());

// Allow requests from the React frontend
app.use(
  cors({
    origin: [
      "http://localhost:5173", // local Vite dev server
      "https://your-app.vercel.app", // production frontend (update later)
    ],
  }),
);

app.use(express.json());

const generalLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 60,
  message: { error: "Too many requests, please slow down" },
});

const scraperLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 240,
  message: { error: "Too many requests, please slow down" },
});

app.use((req, res, next) => {
  if (req.path.startsWith("/api/scraper")) return next();
  return generalLimiter(req, res, next);
});

// Health check — Railway uses this to confirm the server is alive
app.get("/health", (req, res) => res.json({ status: "ok" }));

// API routes
app.use("/api/products", productRoutes);
app.use("/api/scraper", scraperLimiter, scraperRoutes);

// Global error handler (must be last)
app.use(errorHandler);

app.listen(PORT, () => {
  console.log(`Backend running on http://localhost:${PORT}`);
});
