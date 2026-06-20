import { createJob, deleteJob, getHealth, uploadFile } from "./api.js";
import { collectJobPayload, renderOperationFields } from "./operations.js";
import { watchJob } from "./job-events.js";

const state = {
  fileId: null,
  currentJobId: null,
  watcher: null,
};

const els = {
  healthPill: document.getElementById("healthPill"),
  healthText: document.getElementById("healthText"),
  dropZone: document.getElementById("dropZone"),
  fileInput: document.getElementById("fileInput"),
  uploadHint: document.getElementById("uploadHint"),
  fileCard: document.getElementById("fileCard"),
  fileName: document.getElementById("fileName"),
  fileSize: document.getElementById("fileSize"),
  fileDuration: document.getElementById("fileDuration"),
  fileStreams: document.getElementById("fileStreams"),
  jobForm: document.getElementById("jobForm"),
  operation: document.getElementById("operation"),
  operationFields: document.getElementById("operationFields"),
  submitJob: document.getElementById("submitJob"),
  jobStatusCard: document.getElementById("jobStatusCard"),
  jobMessage: document.getElementById("jobMessage"),
  jobState: document.getElementById("jobState"),
  progressFill: document.getElementById("progressFill"),
  progressText: document.getElementById("progressText"),
  downloadLink: document.getElementById("downloadLink"),
  deleteJob: document.getElementById("deleteJob"),
  clearLog: document.getElementById("clearLog"),
  logOutput: document.getElementById("logOutput"),
  toast: document.getElementById("toast"),
};

init();

function init() {
  renderOperationFields(els.operationFields, els.operation.value);
  bindEvents();
  checkHealth();
}

function bindEvents() {
  els.operation.addEventListener("change", () => {
    renderOperationFields(els.operationFields, els.operation.value);
  });

  els.fileInput.addEventListener("change", () => {
    const file = els.fileInput.files?.[0];
    if (file) {
      handleUpload(file);
    }
  });

  els.dropZone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      els.fileInput.click();
    }
  });

  for (const type of ["dragenter", "dragover"]) {
    els.dropZone.addEventListener(type, (event) => {
      event.preventDefault();
      els.dropZone.classList.add("is-over");
    });
  }

  for (const type of ["dragleave", "drop"]) {
    els.dropZone.addEventListener(type, (event) => {
      event.preventDefault();
      els.dropZone.classList.remove("is-over");
    });
  }

  els.dropZone.addEventListener("drop", (event) => {
    const file = event.dataTransfer?.files?.[0];
    if (file) {
      handleUpload(file);
    }
  });

  els.jobForm.addEventListener("submit", (event) => {
    event.preventDefault();
    submitJob();
  });

  els.deleteJob.addEventListener("click", () => {
    cleanupCurrentJob();
  });

  els.clearLog.addEventListener("click", () => {
    els.logOutput.textContent = "";
  });
}

async function checkHealth() {
  try {
    const health = await getHealth();
    if (health.ok) {
      els.healthPill.dataset.state = "ok";
      els.healthText.textContent = "ffmpeg ready";
      return;
    }
    els.healthPill.dataset.state = "error";
    els.healthText.textContent = "ffmpeg unavailable";
  } catch (error) {
    els.healthPill.dataset.state = "error";
    els.healthText.textContent = "backend offline";
    showToast(error.message);
  }
}

async function handleUpload(file) {
  resetJobUi();
  els.submitJob.disabled = true;
  els.uploadHint.textContent = "上传中";
  els.fileName.textContent = file.name;
  els.fileSize.textContent = formatBytes(file.size);
  els.fileDuration.textContent = "-";
  els.fileStreams.textContent = "-";
  els.fileCard.classList.remove("is-empty");

  try {
    const result = await uploadFile(file);
    state.fileId = result.file_id;
    renderMediaInfo(result);
    els.uploadHint.textContent = "上传完成";
    els.submitJob.disabled = false;
    showToast("文件已就绪");
  } catch (error) {
    state.fileId = null;
    els.uploadHint.textContent = "上传失败";
    els.fileCard.classList.add("is-empty");
    els.submitJob.disabled = true;
    showToast(error.message);
  }
}

async function submitJob() {
  if (!state.fileId) {
    showToast("请先上传文件");
    return;
  }

  els.submitJob.disabled = true;
  setJobStatus({ status: "pending", message: "创建任务", progress: 0, logs_tail: [] });
  try {
    const payload = collectJobPayload(els.jobForm, state.fileId);
    const created = await createJob(payload);
    state.currentJobId = created.job_id;
    els.deleteJob.disabled = false;
    startWatching(created.job_id);
  } catch (error) {
    els.submitJob.disabled = false;
    setJobStatus({ status: "failed", message: error.message, progress: 0, logs_tail: [] });
    showToast(error.message);
  }
}

function startWatching(jobId) {
  if (state.watcher) {
    state.watcher.close();
  }
  state.watcher = watchJob(jobId, {
    onUpdate(data) {
      setJobStatus(data);
    },
    onFallback() {
      appendLog("SSE unavailable; using polling.");
    },
    onError(error) {
      appendLog(`Polling error: ${error.message}`);
    },
  });
}

function setJobStatus(job) {
  els.jobStatusCard.dataset.state = job.status;
  els.jobMessage.textContent = job.message || job.status;
  els.jobState.textContent = job.status;

  if (typeof job.progress === "number") {
    const pct = Math.round(job.progress * 100);
    els.progressFill.style.width = `${pct}%`;
    els.progressText.textContent = `${pct}%`;
  } else {
    els.progressFill.style.width = "100%";
    els.progressText.textContent = "running";
  }

  if (Array.isArray(job.logs_tail)) {
    els.logOutput.textContent = job.logs_tail.length ? job.logs_tail.join("\n") : els.logOutput.textContent;
    els.logOutput.scrollTop = els.logOutput.scrollHeight;
  }

  if (job.status === "succeeded" && job.download_url) {
    els.downloadLink.href = job.download_url;
    els.downloadLink.classList.remove("is-disabled");
    els.downloadLink.download = job.output_name || "output";
    els.submitJob.disabled = false;
    showToast("处理完成");
    return;
  }

  if (["failed", "cancelled"].includes(job.status)) {
    els.submitJob.disabled = false;
    showToast(job.message || job.status);
  }
}

async function cleanupCurrentJob() {
  if (!state.currentJobId) {
    return;
  }
  const jobId = state.currentJobId;
  if (state.watcher) {
    state.watcher.close();
    state.watcher = null;
  }
  try {
    await deleteJob(jobId);
    state.currentJobId = null;
    resetJobUi();
    showToast("任务已清理");
  } catch (error) {
    showToast(error.message);
  }
}

function resetJobUi() {
  if (state.watcher) {
    state.watcher.close();
    state.watcher = null;
  }
  state.currentJobId = null;
  els.deleteJob.disabled = true;
  els.downloadLink.href = "#";
  els.downloadLink.classList.add("is-disabled");
  els.progressFill.style.width = "0%";
  els.progressText.textContent = "0%";
  els.jobMessage.textContent = "等待任务";
  els.jobState.textContent = "idle";
  els.jobStatusCard.dataset.state = "idle";
  els.logOutput.textContent = "Ready.";
}

function renderMediaInfo(result) {
  els.fileName.textContent = result.original_name;
  els.fileSize.textContent = formatBytes(result.size);

  const duration = Number(result.media_info?.format?.duration);
  els.fileDuration.textContent = Number.isFinite(duration) ? formatDuration(duration) : "duration -";

  const streams = Array.isArray(result.media_info?.streams) ? result.media_info.streams : [];
  const video = streams.find((stream) => stream.codec_type === "video");
  const audio = streams.find((stream) => stream.codec_type === "audio");
  const parts = [];
  if (video) {
    parts.push(`${video.width || "-"}x${video.height || "-"}`);
  }
  if (audio) {
    parts.push(audio.codec_name || "audio");
  }
  els.fileStreams.textContent = parts.length ? parts.join(" / ") : "streams -";
}

function appendLog(line) {
  const current = els.logOutput.textContent.trim();
  els.logOutput.textContent = current ? `${current}\n${line}` : line;
  els.logOutput.scrollTop = els.logOutput.scrollHeight;
}

function showToast(message) {
  if (!message) {
    return;
  }
  els.toast.textContent = message;
  els.toast.classList.add("is-visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    els.toast.classList.remove("is-visible");
  }, 3200);
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) {
    return "-";
  }
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(value >= 10 || unit === 0 ? 0 : 1)} ${units[unit]}`;
}

function formatDuration(seconds) {
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return `${minutes}:${String(rest).padStart(2, "0")}`;
}

