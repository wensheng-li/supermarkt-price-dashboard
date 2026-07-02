import { Router } from "express";
import {
  cancelScraperJob,
  getScraperJobStatus,
} from "../services/scraperQueue.js";

const router = Router();

// Get job status — tries Bull job first, then falls back to Redis persisted metadata.
router.get("/status/:jobId", async (req, res) => {
  const { jobId } = req.params;
  try {
    const status = await getScraperJobStatus(jobId);
    if (!status) return res.status(404).json({ error: "Job not found" });
    return res.json({ id: jobId, ...status });
  } catch (err) {
    console.error("[scraper route] error", err);
    return res.status(500).json({ error: "Internal error" });
  }
});

// Cancel a queued or active scraper job.
router.post("/cancel/:jobId", async (req, res) => {
  const { jobId } = req.params;
  try {
    const result = await cancelScraperJob(jobId);
    if (!result) return res.status(404).json({ error: "Job not found" });
    return res.json(result);
  } catch (err) {
    console.error("[scraper route] error", err);
    return res.status(500).json({ error: "Internal error" });
  }
});

export default router;
