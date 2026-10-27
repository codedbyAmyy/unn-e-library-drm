import { apiRequest } from "./api.js";

const issueTypes = [
  ["file_unavailable", "File is missing or unavailable"],
  ["file_corrupted", "PDF is corrupted / won't open"],
  ["incorrect_metadata", "Incorrect resource information"],
  ["access_problem", "Access or permission problem"],
  ["other", "Other issue"],
];

export function openReportResourceIssue(resource) {
  const id = Number(resource?.id);
  if (!Number.isInteger(id) || id <= 0) return;
  const overlay = document.createElement("div");
  overlay.className = "unn-report-modal-backdrop";
  const dialog = document.createElement("form");
  dialog.className = "unn-report-modal";
  dialog.setAttribute("role", "dialog");
  dialog.setAttribute("aria-modal", "true");
  dialog.setAttribute("aria-labelledby", "unn-report-title");
  const title = document.createElement("h2");
  title.id = "unn-report-title";
  title.textContent = "Report a Resource Issue";
  const subtitle = document.createElement("p");
  subtitle.textContent = resource.title || "Academic resource";
  const typeLabel = document.createElement("label");
  typeLabel.textContent = "What is the problem?";
  const select = document.createElement("select");
  select.required = true;
  for (const [value, label] of issueTypes) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.append(option);
  }
  typeLabel.append(select);
  const descLabel = document.createElement("label");
  descLabel.textContent = "Describe the issue (optional)";
  const description = document.createElement("textarea");
  description.maxLength = 2000;
  description.placeholder = "Explain what happened so the librarian can investigate…";
  descLabel.append(description);
  const status = document.createElement("p");
  status.setAttribute("role", "alert");
  const actions = document.createElement("div");
  actions.className = "unn-report-modal-actions";
  const cancel = document.createElement("button");
  cancel.type = "button";
  cancel.textContent = "Cancel";
  const submit = document.createElement("button");
  submit.type = "submit";
  submit.textContent = "Submit Report";
  actions.append(cancel, submit);
  dialog.append(title, subtitle, typeLabel, descLabel, status, actions);
  overlay.append(dialog);
  document.body.append(overlay);
  const restoreFocus = document.activeElement;
  let busy = false;
  function close() {
    if (busy) return;
    overlay.remove();
    document.removeEventListener("keydown", onKey);
    restoreFocus?.focus?.();
  }
  function onKey(event) { if (event.key === "Escape") close(); }
  document.addEventListener("keydown", onKey);
  cancel.addEventListener("click", close);
  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  dialog.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy) return;
    busy = true;
    submit.disabled = true;
    cancel.disabled = true;
    status.textContent = "Submitting your report…";
    try {
      await apiRequest("/reports", {
        method: "POST",
        body: JSON.stringify({
          resource_id: id,
          issue_type: select.value,
          description: description.value.trim() || null,
        }),
      });
      status.style.color = "#06704b";
      status.textContent = "Report submitted successfully. A librarian can now review it.";
      submit.remove();
      cancel.textContent = "Close";
    } catch (error) {
      status.textContent = `Could not submit report: ${error.message || "Please try again."}`;
      submit.disabled = false;
    } finally {
      busy = false;
      cancel.disabled = false;
    }
  });
  select.focus();
}
