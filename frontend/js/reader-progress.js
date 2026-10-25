import { API_BASE, getToken, handleSessionExpired } from "./api.js";

const $ = (id) => document.getElementById(id);
const resourceId = Number(new URLSearchParams(location.search).get("resource"));
let documentPdf = null;
let protectedPdfBlob = null;
let currentPage = 1;
let totalPages = 0;
let busy = false;
let pendingPage = null;
let zoom = 1;
let pendingZoom = false;
const MIN_ZOOM = 0.5;
const MAX_ZOOM = 2.5;
const ZOOM_STEP = 0.25;

function updateZoomUi() {
  $("zoom-label").textContent = `${Math.round(zoom * 100)}%`;
  $("zoom-out").disabled = zoom <= MIN_ZOOM;
  $("zoom-in").disabled = zoom >= MAX_ZOOM;
  $("zoom-reset").disabled = zoom === 1;
}
function changeZoom(nextZoom) {
  const bounded = Math.max(
    MIN_ZOOM,
    Math.min(MAX_ZOOM, Math.round(nextZoom * 100) / 100),
  );
  if (bounded === zoom) return;
  zoom = bounded;
  updateZoomUi();
  // A busy render must be redrawn even if the page number has not changed.
  if (busy) {
    pendingPage = currentPage;
    pendingZoom = true;
  } else if (documentPdf) void renderPage(currentPage);
}

function message(text = "", isError = false) {
  const element = $("reader-state");
  element.textContent = text;
  element.classList.toggle("reader-error", isError);
}
function setLoading(active, heading = "", detail = "") {
  $("reader-loading").hidden = !active;
  $("pdf-stage").setAttribute("aria-busy", String(active));
  if (heading) $("reader-loading-heading").textContent = heading;
  if (detail) $("reader-loading-detail").textContent = detail;
}
async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${getToken() || ""}`,
      ...options.headers,
    },
    cache: "no-store",
  });
  if (response.status === 401) {
    handleSessionExpired();
    throw new Error('Session expired. Redirecting to sign in.');
  }
  if (!response.ok) {
    let detail = "";
    try {
      detail = (await response.json()).detail;
    } catch {}
    throw new Error(
      typeof detail === "string"
        ? detail
        : `Request failed (${response.status})`,
    );
  }
  return response;
}

async function renderPage(page) {
  if (busy) {
    pendingPage = page;
    return;
  }
  busy = true;
  setLoading(
    true,
    `Opening page ${page}`,
    "Making the page ready for reading…",
  );
  message("");
  try {
    const pdfPage = await documentPdf.getPage(page);
    const initial = pdfPage.getViewport({ scale: 1 });
    const targetWidth = Math.max(
      280,
      Math.min(1100, $("pdf-stage").clientWidth - 32),
    );
    const viewport = pdfPage.getViewport({
      scale: (targetWidth / initial.width) * zoom,
    });
    const canvas = $("pdf-canvas");
    const pixelRatio = Math.min(
      window.devicePixelRatio || 1,
      zoom > 1.5 ? 1.25 : 2,
    );
    canvas.width = Math.floor(viewport.width * pixelRatio);
    canvas.height = Math.floor(viewport.height * pixelRatio);
    canvas.style.width = `${Math.round(viewport.width)}px`;
    canvas.style.height = `${Math.round(viewport.height)}px`;
    const context = canvas.getContext("2d");
    await pdfPage.render({
      canvasContext: context,
      viewport,
      transform: pixelRatio === 1 ? null : [pixelRatio, 0, 0, pixelRatio, 0, 0],
    }).promise;

    currentPage = page;
    $("page").value = String(page);
    $("prev").disabled = page <= 1;
    $("next").disabled = page >= totalPages;
    const percentage = Math.round((100 * page) / totalPages);
    $("progress-label").textContent = `${percentage}% reached`;
    $("progress-fill").style.width = `${percentage}%`;
    $("progress-track").setAttribute("aria-valuenow", String(percentage));
    setLoading(false);

    try {
      await request(`/reading-progress/${resourceId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_page: page, total_pages: totalPages }),
      });
    } catch (error) {
      message(
        `Page displayed, but reading position could not be saved: ${error.message}`,
        true,
      );
    }
  } catch (error) {
    setLoading(false);
    message(`Unable to display page ${page}: ${error.message}`, true);
  } finally {
    busy = false;
    if (pendingPage !== null) {
      const next = pendingPage;
      const zoomChanged = pendingZoom;
      pendingPage = null;
      pendingZoom = false;
      if (next !== currentPage || zoomChanged) void renderPage(next);
    }
  }
}

function go(page) {
  if (!Number.isInteger(page) || page < 1 || page > totalPages) {
    $("page").value = String(currentPage);
    return;
  }
  void renderPage(page);
}

function downloadProtectedPdf() {
  if (!protectedPdfBlob) return;
  // Download exactly the personalized bytes retrieved from /resources/{id}/read.
  // Never request the original uploaded file or construct a public storage URL.
  const url = URL.createObjectURL(protectedPdfBlob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `UNN-protected-resource-${resourceId}.pdf`;
  document.body.append(link);
  link.click();
  link.remove();
  // Keep the temporary browser URL briefly while the download begins.
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

async function boot() {
  setLoading(
    true,
    "Preparing your protected document",
    "Opening your secure reading copy…",
  );
  if (!Number.isInteger(resourceId) || resourceId <= 0) {
    setLoading(false);
    message("Invalid resource link.", true);
    return;
  }
  if (!getToken()) {
    handleSessionExpired();
    return;
  }
  if (!window.pdfjsLib) {
    setLoading(false);
    message(
      "The PDF viewer library could not load. Check your internet connection and refresh.",
      true,
    );
    return;
  }
  window.pdfjsLib.GlobalWorkerOptions.workerSrc =
    "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
  try {
    // Get title without blocking the protected PDF if metadata is unavailable.
    try {
      const metadata = await (await request(`/resources/${resourceId}`)).json();
      $("resource-name").textContent =
        metadata.title || `Resource #${resourceId}`;
      document.title = `${metadata.title || "Protected resource"} · UNN E-Library`;
    } catch {
      $("resource-name").textContent = `Resource #${resourceId}`;
    }

    const pdfResponse = await request(`/resources/${resourceId}/read`);
    const pdfBytes = await pdfResponse.arrayBuffer();
    // PDF.js may transfer its ArrayBuffer to a worker. Keep an independent copy
    // so the protected download remains available after rendering.
    protectedPdfBlob = new Blob([pdfBytes.slice(0)], {
      type: "application/pdf",
    });
    $("download-pdf").disabled = false;
    $("download-pdf").addEventListener("click", downloadProtectedPdf);
    setLoading(true, "Opening protected PDF", "Getting your pages ready…");
    documentPdf = await window.pdfjsLib.getDocument({
      data: new Uint8Array(pdfBytes),
    }).promise;
    totalPages = documentPdf.numPages;
    if (!totalPages)
      throw new Error("The protected PDF contains no readable pages.");
    $("total").textContent = String(totalPages);
    $("reader-controls").hidden = false;
    let startPage = 1;
    try {
      const progress = await (
        await request(`/reading-progress/${resourceId}`)
      ).json();
      if (
        progress.total_pages === totalPages &&
        progress.current_page >= 1 &&
        progress.current_page <= totalPages
      ) {
        startPage = progress.current_page;
      }
    } catch {
      // Missing reading-history record is fine; start from page one.
    }
    updateZoomUi();
    $("zoom-out").addEventListener("click", () => changeZoom(zoom - ZOOM_STEP));
    $("zoom-in").addEventListener("click", () => changeZoom(zoom + ZOOM_STEP));
    $("zoom-reset").addEventListener("click", () => changeZoom(1));
    $("prev").addEventListener("click", () => go(currentPage - 1));
    $("next").addEventListener("click", () => go(currentPage + 1));
    $("page").max = String(totalPages);
    $("page").addEventListener("change", () => go(Number($("page").value)));
    document.addEventListener("keydown", (event) => {
      if (
        event.target instanceof Element &&
        event.target.matches("input,textarea")
      )
        return;
      if (event.key === "ArrowRight") go(currentPage + 1);
      if (event.key === "ArrowLeft") go(currentPage - 1);
    });
    void renderPage(startPage);
  } catch (error) {
    setLoading(false);
    $("resource-name").textContent = `Unable to open resource #${resourceId}`;
    message(`Cannot open protected PDF: ${error.message}`, true);
  }
}

void boot();
