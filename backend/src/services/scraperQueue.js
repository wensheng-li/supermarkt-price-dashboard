import Bull from "bull";
import path from "path";
import { fileURLToPath } from "url";
import { spawn } from "child_process";
import { createClient } from "redis";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const JOB_METADATA_TTL_SECONDS = Number(
  process.env.SCRAPER_JOB_METADATA_TTL_SECONDS ?? 60 * 30,
);
const activeChildren = new Map();
const cancellingJobs = new Set();

const queue = new Bull(
  "scraper",
  process.env.REDIS_URL || "redis://127.0.0.1:6379",
);

// Redis client for persisting lightweight job metadata
const redisClient = createClient({
  url: process.env.REDIS_URL || "redis://127.0.0.1:6379",
});
redisClient.on("error", (e) => console.error("Redis error", e));
redisClient.connect().catch(() => {});

async function setJobMetadata(jobId, metadata) {
  try {
    await redisClient.setEx(
      `scraper:job:${jobId}`,
      JOB_METADATA_TTL_SECONDS,
      JSON.stringify(metadata),
    );
  } catch (e) {
    console.error("[scraperQueue] Redis set failed", e.message);
  }
}

async function getJobMetadata(jobId) {
  try {
    const raw = await redisClient.get(`scraper:job:${jobId}`);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    console.error("[scraperQueue] Redis get failed", e.message);
    return null;
  }
}

// Process jobs by executing the Python scraper. The job data should include { productName, postcode }
queue.process(async (job) => {
  const { productName, postcode, state } = job.data;
  const SCRAPER_PATH = path.resolve(
    __dirname,
    "../../../scraper/scraper_runner.py",
  );
  const PYTHON_BIN = path.resolve(
    __dirname,
    "../../../scraper/.venv/bin/python3",
  );

  // Persist initial job metadata
  await setJobMetadata(job.id, {
    status: "started",
    progress: 0,
    productName,
    postcode,
    state,
    startedAt: Date.now(),
  });

  return new Promise((resolve, reject) => {
    const args = ["-u", SCRAPER_PATH, productName, postcode || "", state || ""];
    const opts = { cwd: path.resolve(__dirname, "../../../scraper") };

    const child = spawn(PYTHON_BIN, args, opts);
    activeChildren.set(String(job.id), child);

    let stdoutAccum = "";

    child.stdout.on("data", (chunk) => {
      const text = chunk.toString();
      process.stdout.write(`[scraper:${job.id}] ${text}`);
      stdoutAccum += text;

      // Parse lines for progress markers like PROGRESS:NN
      const matches = text.match(/PROGRESS:(\d{1,3})/g);
      if (matches) {
        matches.forEach((m) => {
          const n = Number(m.split(":")[1]);
          job.progress(n);
          // persist progress
          setJobMetadata(job.id, {
            status: "in_progress",
            progress: n,
            productName,
            postcode,
            state,
            updatedAt: Date.now(),
          });
        });
      }
    });

    child.stderr.on("data", (chunk) => {
      process.stderr.write(`[scraper:${job.id}][stderr] ${chunk.toString()}`);
    });

    child.on("error", async (err) => {
      activeChildren.delete(String(job.id));
      console.error("[scraperQueue] spawn error", err.message);
      await setJobMetadata(job.id, {
        status: cancellingJobs.has(String(job.id)) ? "cancelled" : "failed",
        error: err.message,
        productName,
        postcode,
        state,
        updatedAt: Date.now(),
      });
      reject(err);
    });

    child.on("close", async (code, signal) => {
      activeChildren.delete(String(job.id));

      if (cancellingJobs.has(String(job.id))) {
        cancellingJobs.delete(String(job.id));
        await setJobMetadata(job.id, {
          status: "cancelled",
          progress: null,
          productName,
          postcode,
          state,
          code,
          signal,
          updatedAt: Date.now(),
        });
        return reject(new Error("Scraper cancelled"));
      }

      if (code !== 0) {
        const err = new Error(`Scraper exited with code ${code}`);
        console.error("[scraperQueue]", err.message);
        await setJobMetadata(job.id, {
          status: "failed",
          code,
          signal,
          productName,
          postcode,
          state,
          updatedAt: Date.now(),
        });
        return reject(err);
      }

      // Mark completed and persist stdout summary
      await setJobMetadata(job.id, {
        status: "completed",
        progress: 100,
        stdout: stdoutAccum.slice(-10000),
        productName,
        postcode,
        state,
        finishedAt: Date.now(),
      });

      job.progress(100);
      console.log(`[scraperQueue] Job ${job.id} finished`);
      resolve({ stdout: stdoutAccum });
    });
  });
});

export async function getScraperJobStatus(jobId) {
  const metadata = await getJobMetadata(jobId);

  const job = await queue.getJob(jobId);
  if (job) {
    const state = await job.getState();
    let progress = 0;
    try {
      progress = (await job.progress()) || 0;
    } catch (_) {
      progress = job._progress || 0;
    }
    if (metadata?.status === "cancelled" || metadata?.status === "cancelling") {
      return {
        state: metadata.status,
        progress: metadata.progress ?? null,
        meta: metadata,
      };
    }
    return {
      state,
      progress: metadata?.progress ?? progress,
      meta: metadata ?? undefined,
    };
  }

  if (metadata) {
    return {
      state: metadata.status || "unknown",
      progress: metadata.progress ?? null,
      meta: metadata,
    };
  }

  return null;
}

export async function cancelScraperJob(jobId) {
  const jobKey = String(jobId);
  const job = await queue.getJob(jobId);

  if (!job) {
    const metadata = await getJobMetadata(jobId);
    if (!metadata) return null;

    if (["completed", "failed", "cancelled"].includes(metadata.status)) {
      return {
        id: jobId,
        state: metadata.status,
        progress: metadata.progress ?? null,
      };
    }

    await setJobMetadata(jobId, {
      ...metadata,
      status: "cancelled",
      progress: null,
      updatedAt: Date.now(),
    });
    return { id: jobId, state: "cancelled", progress: null };
  }

  const state = await job.getState();

  if (["waiting", "delayed", "paused"].includes(state)) {
    await job.remove();
    const metadata = await getJobMetadata(jobId);
    await setJobMetadata(jobId, {
      ...metadata,
      status: "cancelled",
      progress: null,
      updatedAt: Date.now(),
    });
    return { id: jobId, state: "cancelled", progress: null };
  }

  if (state === "active") {
    const child = activeChildren.get(jobKey);
    cancellingJobs.add(jobKey);
    const metadata = await getJobMetadata(jobId);
    await setJobMetadata(jobId, {
      ...metadata,
      status: "cancelling",
      updatedAt: Date.now(),
    });

    if (child) {
      child.kill("SIGTERM");
      setTimeout(() => {
        if (activeChildren.has(jobKey)) {
          activeChildren.get(jobKey)?.kill("SIGKILL");
        }
      }, 5000).unref();
    }

    return {
      id: jobId,
      state: "cancelling",
      progress: metadata?.progress ?? null,
    };
  }

  return { id: jobId, state };
}

export default queue;
