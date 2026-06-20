import { getJob } from "./api.js";

export function watchJob(jobId, handlers) {
  if ("EventSource" in window) {
    return watchWithSse(jobId, handlers);
  }
  return watchWithPolling(jobId, handlers);
}

function watchWithSse(jobId, handlers) {
  const source = new EventSource(`/api/jobs/${encodeURIComponent(jobId)}/events`);
  let closed = false;
  let fallbackStarted = false;

  source.addEventListener("update", (event) => {
    const data = JSON.parse(event.data);
    handlers.onUpdate(data);
    if (isTerminal(data.status)) {
      closed = true;
      source.close();
    }
  });

  source.onerror = () => {
    if (closed || fallbackStarted) {
      return;
    }
    fallbackStarted = true;
    source.close();
    handlers.onFallback?.();
    watchWithPolling(jobId, handlers);
  };

  return {
    close() {
      closed = true;
      source.close();
    },
  };
}

function watchWithPolling(jobId, handlers) {
  let stopped = false;
  let timer = null;

  const tick = async () => {
    if (stopped) {
      return;
    }
    try {
      const data = await getJob(jobId);
      handlers.onUpdate(data);
      if (isTerminal(data.status)) {
        stopped = true;
        return;
      }
    } catch (error) {
      handlers.onError?.(error);
    }
    timer = window.setTimeout(tick, 1200);
  };

  tick();
  return {
    close() {
      stopped = true;
      if (timer) {
        window.clearTimeout(timer);
      }
    },
  };
}

function isTerminal(status) {
  return ["succeeded", "failed", "cancelled"].includes(status);
}

