"use strict";

const byId = (id) => document.getElementById(id);

const elements = {
  form: byId("stream-form"),
  source: byId("source"),
  edgeDevice: byId("edge-device-id"),
  vehicle: byId("vehicle-id"),
  route: byId("route-id"),
  maxFrames: byId("max-frames"),
  realtime: byId("realtime"),
  start: byId("start-button"),
  stop: byId("stop-button"),
  notice: byId("notice"),
  healthDot: byId("health-dot"),
  healthLabel: byId("health-label"),
  modelLabel: byId("model-label"),
  sessionState: byId("session-state"),
  sessionDetail: byId("session-detail"),
  sourceLabel: byId("source-label"),
  frame: byId("stream-frame"),
  viewerEmpty: byId("viewer-empty"),
  frameCount: byId("frame-count"),
  inferenceMs: byId("inference-ms"),
  visibleCounts: byId("visible-counts"),
  uniqueCounts: byId("unique-counts"),
  totalRuns: byId("total-runs"),
  totalObserved: byId("total-observed"),
  pendingReview: byId("pending-review"),
  confirmedCollected: byId("confirmed-collected"),
  runsBody: byId("runs-body"),
  reviewBody: byId("review-body"),
  refresh: byId("refresh-button"),
  demoSource: byId("demo-source-button"),
  imageInput: byId("image-input"),
  imageCanvas: byId("image-canvas"),
  imagePlaceholder: byId("image-placeholder"),
};

let activeSessionId = null;
let statusTimer = null;
let frameTimer = null;
let detectionEnabled = true;

async function api(path, options = {}) {
  const response = await fetch(path, {
    cache: "no-store",
    ...options,
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch (_) {
      // The response was not JSON.
    }
    throw new Error(detail);
  }
  return response;
}

function showNotice(message, error = false) {
  elements.notice.hidden = !message;
  elements.notice.textContent = message || "";
  elements.notice.classList.toggle("error", error);
}

function formatName(value) {
  return String(value || "").replaceAll("_", " ");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function totalCounts(counts = {}) {
  return Object.values(counts).reduce((total, count) => total + Number(count), 0);
}

function renderCounts(container, counts, emptyText) {
  const entries = Object.entries(counts || {}).filter(([, count]) => count > 0);
  if (!entries.length) {
    container.innerHTML = `<em>${emptyText}</em>`;
    return;
  }
  container.innerHTML = entries
    .sort(([left], [right]) => left.localeCompare(right))
    .map(
      ([name, count]) =>
        `<b>${escapeHtml(formatName(name))} · ${Number(count)}</b>`,
    )
    .join("");
}

function setSessionControls(active) {
  elements.start.disabled = active || !detectionEnabled;
  elements.stop.disabled = !active;
  elements.imageInput.disabled = !detectionEnabled;
  document
    .querySelector(".live-indicator")
    .classList.toggle("active", active);
}

function stopPolling() {
  if (statusTimer) window.clearInterval(statusTimer);
  if (frameTimer) window.clearInterval(frameTimer);
  statusTimer = null;
  frameTimer = null;
}

function terminalStatus(status) {
  return ["completed", "interrupted", "failed"].includes(status);
}

function applyStreamStatus(status) {
  elements.sessionState.textContent =
    status.status.charAt(0).toUpperCase() + status.status.slice(1);
  elements.sessionDetail.textContent =
    status.error || `${status.frames} frames processed`;
  elements.sourceLabel.textContent = status.source || "Connected source";
  elements.frameCount.textContent = status.frames || 0;

  const outcome = status.latest_outcome;
  if (outcome) {
    elements.inferenceMs.textContent = Number(outcome.inference_ms).toFixed(1);
    renderCounts(elements.visibleCounts, outcome.visible_counts, "No detections");
    renderCounts(
      elements.uniqueCounts,
      outcome.unique_session_counts,
      "No confirmed tracks",
    );
  }

  if (status.frame_available) {
    elements.viewerEmpty.style.display = "none";
    elements.frame.classList.add("active");
  }

  if (terminalStatus(status.status)) {
    stopPolling();
    setSessionControls(false);
    activeSessionId = null;
    refreshOperations();
    if (status.status === "failed") {
      showNotice(status.error || "The stream failed.", true);
    } else {
      showNotice(`Session ${status.status}; its counts are stored in SQLite.`);
    }
  }
}

async function pollStatus() {
  if (!activeSessionId) return;
  try {
    const response = await api(`/v1/streams/${activeSessionId}`);
    applyStreamStatus(await response.json());
  } catch (error) {
    showNotice(error.message, true);
  }
}

function refreshFrame() {
  if (!activeSessionId) return;
  elements.frame.src =
    `/v1/streams/${activeSessionId}/frame.jpg?t=${Date.now()}`;
}

async function startStream(event) {
  event.preventDefault();
  showNotice("");
  const payload = {
    source: elements.source.value.trim(),
    edge_device_id: elements.edgeDevice.value.trim() || "edge-node",
    vehicle_id: elements.vehicle.value.trim() || null,
    route_id: elements.route.value.trim() || null,
    realtime: elements.realtime.checked,
    max_frames: Number(elements.maxFrames.value || 0),
  };
  try {
    elements.start.disabled = true;
    elements.start.textContent = "Starting model…";
    const response = await api("/v1/streams", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const status = await response.json();
    activeSessionId = status.session_id;
    setSessionControls(true);
    applyStreamStatus(status);
    await pollStatus();
    statusTimer = window.setInterval(pollStatus, 900);
    frameTimer = window.setInterval(refreshFrame, 250);
  } catch (error) {
    setSessionControls(false);
    showNotice(error.message, true);
  } finally {
    elements.start.textContent = "Start detection";
  }
}

async function stopStream() {
  if (!activeSessionId) return;
  elements.stop.disabled = true;
  try {
    const response = await api(`/v1/streams/${activeSessionId}`, {
      method: "DELETE",
    });
    applyStreamStatus(await response.json());
  } catch (error) {
    showNotice(error.message, true);
    elements.stop.disabled = false;
  }
}

async function refreshHealth() {
  try {
    const response = await api("/healthz");
    const health = await response.json();
    elements.healthDot.className = "status-dot online";
    elements.healthLabel.textContent = `Online · ${health.device}`;
    elements.modelLabel.textContent = health.backend.replaceAll("_", " ");
    detectionEnabled = health.service_mode !== "counts_api";
    setSessionControls(Boolean(activeSessionId));
    if (!detectionEnabled) {
      showNotice(
        "This service is running in counts-only mode. Restart with --dashboard to enable detection.",
      );
    }
  } catch (_) {
    elements.healthDot.className = "status-dot offline";
    elements.healthLabel.textContent = "API unavailable";
  }
}

function renderRuns(runs) {
  if (!runs.length) {
    elements.runsBody.innerHTML =
      '<tr><td colspan="5" class="empty-cell">No completed runs yet.</td></tr>';
    return;
  }
  elements.runsBody.innerHTML = runs
    .slice(0, 8)
    .map((run) => {
      const count = totalCounts(run.unique_detected_counts);
      return `
        <tr>
          <td><span class="status-chip">${escapeHtml(run.status)}</span></td>
          <td title="${escapeHtml(run.source)}">${escapeHtml(run.source)}</td>
          <td>${Number(run.frames)}</td>
          <td>${count}</td>
          <td>${escapeHtml(run.edge_device_id)}</td>
        </tr>`;
    })
    .join("");
}

function renderReviews(reviews) {
  if (!reviews.length) {
    elements.reviewBody.innerHTML =
      '<tr><td colspan="3" class="empty-cell">No pending reviews.</td></tr>';
    return;
  }
  elements.reviewBody.innerHTML = reviews
    .slice(0, 8)
    .map(
      (review) => `
        <tr>
          <td>${escapeHtml(formatName(review.suggested_class_name))}</td>
          <td>${Number(review.confidence).toFixed(2)}</td>
          <td>${escapeHtml(formatName(review.suggested_destination || "manual review"))}</td>
        </tr>`,
    )
    .join("");
}

async function refreshOperations() {
  try {
    const [summaryResponse, runsResponse, reviewResponse] = await Promise.all([
      api("/v1/counts/summary"),
      api("/v1/runs?limit=10"),
      api("/v1/review-queue?status=pending&limit=1000"),
    ]);
    const summary = await summaryResponse.json();
    const runs = await runsResponse.json();
    const reviews = await reviewResponse.json();

    elements.totalRuns.textContent = summary.run_count || 0;
    elements.totalObserved.textContent = totalCounts(
      summary.run_unique_detected_counts,
    );
    elements.confirmedCollected.textContent = totalCounts(
      summary.confirmed_collected_counts,
    );
    elements.pendingReview.textContent = reviews.reviews.length;
    renderRuns(runs.runs || []);
    renderReviews(reviews.reviews || []);
  } catch (error) {
    showNotice(`Operational data: ${error.message}`, true);
  }
}

async function detectImage(file) {
  if (!file) return;
  showNotice("Loading the model and inspecting the image…");
  const image = new Image();
  const objectUrl = URL.createObjectURL(file);
  image.src = objectUrl;
  await image.decode();
  try {
    const response = await api("/v1/detect", {
      method: "POST",
      headers: { "Content-Type": file.type || "image/jpeg" },
      body: file,
    });
    const result = await response.json();
    const canvas = elements.imageCanvas;
    const context = canvas.getContext("2d");
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    context.drawImage(image, 0, 0);
    context.lineWidth = Math.max(2, image.naturalWidth / 400);
    context.font = `${Math.max(15, image.naturalWidth / 45)}px system-ui`;

    for (const detection of result.detections || []) {
      const [x1, y1, x2, y2] = detection.bbox_xyxy;
      const color = detection.review_required ? "#ff7f78" : "#75f0b6";
      const label = `${formatName(detection.class_name)} ${detection.confidence.toFixed(2)}`;
      context.strokeStyle = color;
      context.fillStyle = color;
      context.strokeRect(x1, y1, x2 - x1, y2 - y1);
      const textWidth = context.measureText(label).width + 12;
      const textHeight = Math.max(22, image.naturalWidth / 35);
      context.fillRect(x1, Math.max(0, y1 - textHeight), textWidth, textHeight);
      context.fillStyle = "#03100c";
      context.fillText(label, x1 + 6, Math.max(17, y1 - 5));
    }
    canvas.classList.add("active");
    elements.imagePlaceholder.style.display = "none";
    showNotice(
      `${totalCounts(result.counts)} objects detected in the uploaded image.`,
    );
  } catch (error) {
    showNotice(error.message, true);
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

elements.form.addEventListener("submit", startStream);
elements.stop.addEventListener("click", stopStream);
elements.refresh.addEventListener("click", refreshOperations);
elements.demoSource.addEventListener("click", () => {
  elements.source.value =
    "media/demo-video/recycling-facility.webm";
  showNotice(
    "Selected the recycling-facility conveyor demo. Run prepare_demo_video.py once if it has not been downloaded.",
  );
});
elements.imageInput.addEventListener("change", (event) => {
  detectImage(event.target.files[0]);
});
elements.frame.addEventListener("error", () => {
  if (!elements.frame.classList.contains("active")) {
    elements.viewerEmpty.style.display = "block";
  }
});

async function restoreActiveStream() {
  try {
    const response = await api("/v1/streams");
    const payload = await response.json();
    const active = (payload.streams || []).find(
      (stream) => !terminalStatus(stream.status),
    );
    if (!active) return;
    activeSessionId = active.session_id;
    setSessionControls(true);
    applyStreamStatus(active);
    statusTimer = window.setInterval(pollStatus, 900);
    frameTimer = window.setInterval(refreshFrame, 250);
  } catch (_) {
    // Health polling will surface an unavailable API.
  }
}

refreshHealth();
refreshOperations();
restoreActiveStream();
window.setInterval(refreshHealth, 15000);
window.setInterval(refreshOperations, 10000);
