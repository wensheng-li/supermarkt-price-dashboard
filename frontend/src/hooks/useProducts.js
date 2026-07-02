/**
 * React Query fetches data from the backend and exposes scraper job status
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:3001";

export function useProducts({
  postcode,
  state,
  productName,
  category,
  sort,
  runId,
}) {
  const queryClient = useQueryClient();
  const restartedRunRef = useRef(null);
  const [jobStatus, setJobStatus] = useState({
    jobId: null,
    progress: null,
    state: null,
  });
  const [isStopping, setIsStopping] = useState(false);

  const params = { postcode, state, productName, category, sort };

  const query = useQuery({
    queryKey: ["products", postcode, state, productName, category, sort, runId],
    queryFn: async () => {
      const shouldRestartScrape =
        Boolean(runId) && restartedRunRef.current !== runId;
      const { data } = await axios.get(`${API_BASE}/api/products/search`, {
        params: {
          ...params,
          ...(shouldRestartScrape && { restart: "true" }),
        },
        timeout: 90000,
      });
      if (shouldRestartScrape) restartedRunRef.current = runId;
      return data;
    },
    enabled: Boolean(postcode && productName && runId),
    staleTime: 1000 * 60 * 5,
  });

  const activeJobId =
    query.data?.status === "scraping" ? query.data.jobId : null;

  useEffect(() => {
    let cancelled = false;
    let timer = null;

    async function poll(delay = 3000) {
      try {
        const resp = await axios.get(
          `${API_BASE}/api/scraper/status/${activeJobId}`,
        );
        const jobState = resp.data?.state;
        const progress =
          typeof resp.data?.progress === "number" ? resp.data.progress : null;
        if (!cancelled) {
          setJobStatus({ jobId: activeJobId, progress, state: jobState });
        }

        if (jobState === "completed") {
          // refresh products
          await queryClient.invalidateQueries({
            queryKey: [
              "products",
              postcode,
              state,
              productName,
              category,
              sort,
              runId,
            ],
          });
          if (!cancelled) {
            setJobStatus({
              jobId: activeJobId,
              progress: 100,
              state: "completed",
            });
          }
          return;
        }
        if (["cancelled", "failed"].includes(jobState)) {
          if (!cancelled) {
            setJobStatus({
              jobId: activeJobId,
              progress: null,
              state: jobState,
            });
          }
          return;
        }
      } catch (err) {
        const status = err?.response?.status;
        if (status === 429) {
          delay = Math.min(10000, delay + 2000);
        }
      }
      if (!cancelled) timer = setTimeout(() => poll(delay), delay);
    }

    if (activeJobId) poll();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [
    activeJobId,
    category,
    postcode,
    productName,
    queryClient,
    runId,
    sort,
    state,
  ]);

  const stopScraping = useCallback(async () => {
    if (!activeJobId) return;

    setIsStopping(true);
    try {
      const { data } = await axios.post(
        `${API_BASE}/api/scraper/cancel/${activeJobId}`,
      );
      setJobStatus({
        jobId: activeJobId,
        progress: data?.progress ?? null,
        state: data?.state ?? "cancelling",
      });
    } finally {
      setIsStopping(false);
    }
  }, [activeJobId]);

  const jobProgress =
    activeJobId && jobStatus.jobId === activeJobId ? jobStatus.progress : 0;
  const jobState =
    activeJobId && jobStatus.jobId === activeJobId ? jobStatus.state : null;

  return {
    ...query,
    jobId: activeJobId,
    jobProgress,
    jobState,
    isStopping,
    stopScraping,
  };
}
