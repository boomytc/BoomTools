const JSON_HEADERS = { "Content-Type": "application/json" };

export async function getHealth() {
  return fetchJson("/api/health");
}

export async function uploadFile(file) {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch("/api/uploads", {
    method: "POST",
    body: form,
  });
  return parseResponse(response);
}

export async function uploadAsset(fileId, file, kind) {
  const form = new FormData();
  form.append("file", file);
  form.append("kind", kind);
  const response = await fetch(`/api/uploads/${encodeURIComponent(fileId)}/assets`, {
    method: "POST",
    body: form,
  });
  return parseResponse(response);
}

export async function createJob(payload) {
  const response = await fetch("/api/jobs", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(payload),
  });
  return parseResponse(response);
}

export async function getJob(jobId) {
  return fetchJson(`/api/jobs/${encodeURIComponent(jobId)}`);
}

export async function deleteJob(jobId) {
  const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`, {
    method: "DELETE",
  });
  return parseResponse(response);
}

async function fetchJson(url) {
  const response = await fetch(url);
  return parseResponse(response);
}

async function parseResponse(response) {
  const text = await response.text();
  let data = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch (error) {
      throw new Error(`Invalid JSON response: ${error.message}`);
    }
  }
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : response.statusText;
    throw new Error(detail || `HTTP ${response.status}`);
  }
  return data;
}
