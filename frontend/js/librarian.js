import { apiRequest, API_BASE, getToken } from "./api.js";

// Works with the existing dashboard, without changing auth or PDF handling.
const types = [
  "book",
  "journal",
  "article",
  "thesis",
  "dissertation",
  "lecture_note",
  "conference_paper",
  "research_paper",
  "report",
  "other",
];
const node = (tag, className = "", text = "") => {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = text;
  return element;
};
const action = (label, handler, quiet = false) => {
  const button = node("button", quiet ? "btn-quiet" : "btn-primary-alt", label);
  button.type = "button";
  button.addEventListener("click", handler);
  return button;
};
const statusOf = (r) =>
  r.is_archived ? "Archived" : r.is_published ? "Published" : "Draft";
const errText = (e) => e?.message || "An unexpected error occurred.";

/** Real browser-to-the server transfer progress; secure storage processing has no % API. */
function sendPdfWithProgress(resourceId, file, onUpdate) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/resources/${resourceId}/files`);
    xhr.setRequestHeader("Authorization", `Bearer ${getToken() || ""}`);
    xhr.responseType = "json";
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && event.total > 0) {
        onUpdate({
          phase: "transfer",
          percent: Math.min(
            100,
            Math.round((event.loaded / event.total) * 100),
          ),
        });
      } else {
        onUpdate({ phase: "transfer", percent: null });
      }
    };
    xhr.upload.onload = () => onUpdate({ phase: "server" });
    xhr.onerror = () =>
      reject(
        new Error(
          "Network connection interrupted while uploading the PDF. Check the resource before trying again.",
        ),
      );
    xhr.onabort = () =>
      reject(
        new Error(
          "Upload was interrupted. Check the resource before trying again.",
        ),
      );
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        onUpdate({ phase: "complete" });
        resolve(xhr.response);
      } else {
        const detail = xhr.response?.detail;
        reject(
          new Error(
            typeof detail === "string"
              ? detail
              : `PDF upload failed (HTTP ${xhr.status}).`,
          ),
        );
      }
    };
    const formData = new FormData();
    formData.append("file", file, file.name);
    onUpdate({ phase: "transfer", percent: 0 });
    xhr.send(formData);
  });
}

function makeUploadTracker(container) {
  const wrapper = node("div", "unn-progress");
  wrapper.hidden = true;
  wrapper.setAttribute("role", "status");
  wrapper.setAttribute("aria-live", "polite");
  const heading = node("div", "unn-progress-label", "Preparing upload…");
  const track = node("div", "unn-progress-track");
  const fill = node("div", "unn-progress-fill");
  track.setAttribute("role", "progressbar");
  track.setAttribute("aria-label", "PDF transfer to E-Library backend");
  track.setAttribute("aria-valuemin", "0");
  track.setAttribute("aria-valuemax", "100");
  track.append(fill);
  const detail = node("p", "unn-progress-detail", "");
  const timer = node("p", "unn-progress-timer", "");
  wrapper.append(heading, track, detail, timer);
  container.append(wrapper);
  let started = 0;
  let interval = null;
  function start() {
    wrapper.hidden = false;
    started = Date.now();
    clearInterval(interval);
    interval = setInterval(() => {
      const secs = Math.floor((Date.now() - started) / 1000);
      timer.textContent = `Elapsed: ${Math.floor(secs / 60)}m ${String(secs % 60).padStart(2, "0")}s`;
    }, 1000);
    timer.textContent = "Elapsed: 0m 00s";
  }
  function update({ phase, percent }) {
    wrapper.hidden = false;
    const isTransfer = phase === "transfer" && Number.isFinite(percent);
    if (isTransfer) track.setAttribute("aria-valuenow", String(percent));
    else track.removeAttribute("aria-valuenow");
    track.classList.toggle("indeterminate", !isTransfer);
    fill.style.width = isTransfer ? `${percent}%` : "";
    if (phase === "draft") {
      heading.textContent = "Step 1 of 3 · Creating resource draft";
      detail.textContent = "Saving resource details to the E-Library database.";
    } else if (phase === "transfer") {
      heading.textContent = isTransfer
        ? `Sending PDF · ${percent}%`
        : "Sending PDF to E-Library…";
      detail.textContent =
        "This percentage measures transfer from your browser to the server, not saving to private storage.";
    } else if (phase === "server") {
      heading.textContent = "PDF received · Securing in private storage";
      detail.textContent =
        "the server is processing the PDF and waiting for secure storage confirmation. This may take a minute or two.";
    } else if (phase === "publish") {
      heading.textContent = "Final step · Publishing resource";
      detail.textContent =
        "Checking the attached PDF and updating the catalogue.";
    } else if (phase === "complete") {
      heading.textContent = "PDF saved successfully";
      detail.textContent =
        "Private storage and file registration confirmed by the server.";
      track.classList.remove("indeterminate");
      fill.style.width = "100%";
      track.setAttribute("aria-valuenow", "100");
    } else if (phase === "error") {
      heading.textContent = "Upload was not completed";
      detail.textContent =
        "Check the resource status before retrying to avoid a duplicate upload.";
      track.classList.remove("indeterminate");
    }
  }
  function stop() {
    clearInterval(interval);
    interval = null;
  }
  return { start, update, stop, element: wrapper };
}

function openDialog({
  heading,
  explanation = "",
  content,
  confirmText = "Continue",
  danger = false,
  onConfirm,
}) {
  const backdrop = node("div", "upload-backdrop");
  const dialog = node("section", "upload-dialog mini-dialog");
  dialog.setAttribute("role", "dialog");
  dialog.setAttribute("aria-modal", "true");
  const headingId = "dialog-heading-" + Math.random().toString(36).slice(2);
  dialog.setAttribute("aria-labelledby", headingId);
  const header = node("div", "upload-header");
  const title = node("h2", "", heading);
  title.id = headingId;
  const close = action("✕", dismiss, true);
  close.setAttribute("aria-label", "Close dialog");
  header.append(title, close);
  dialog.append(header);
  if (explanation) dialog.append(node("p", "dialog-explanation", explanation));
  if (content) dialog.append(content);
  const feedback = node("p", "form-feedback dialog-feedback");
  feedback.setAttribute("role", "alert");
  dialog.append(feedback);
  const footer = node("div", "upload-footer dialog-actions");
  const cancel = action("Cancel", dismiss, true);
  const accept = action(confirmText, async () => {
    accept.disabled = true;
    cancel.disabled = true;
    close.disabled = true;
    try {
      await onConfirm(feedback);
      dismiss();
    } catch (e) {
      feedback.textContent = errText(e);
      accept.disabled = false;
      cancel.disabled = false;
      close.disabled = false;
    }
  });
  if (danger) accept.classList.add("danger-action");
  footer.append(cancel, accept);
  dialog.append(footer);
  backdrop.append(dialog);
  const formerFocus = document.activeElement;
  function dismiss() {
    backdrop.remove();
    document.removeEventListener("keydown", onKey);
    formerFocus?.focus?.();
  }
  function onKey(e) {
    if (e.key === "Escape" && !accept.disabled) dismiss();
  }
  document.addEventListener("keydown", onKey);
  document.body.append(backdrop);
  cancel.focus();
  return { dismiss, feedback };
}

async function uploadPdfForDraft(resource, refresh) {
  const container = node("div", "dialog-body");
  const picker = node("input", "field-input");
  picker.type = "file";
  picker.accept = ".pdf,application/pdf";
  const help = node(
    "p",
    "upload-note",
    "Select the PDF for this existing resource. No new resource or duplicate draft will be created. Maximum file size: 50 MB.",
  );
  container.append(picker, help);
  const tracker = makeUploadTracker(container);
  openDialog({
    heading: "Attach PDF to existing draft",
    explanation: resource.title,
    content: container,
    confirmText: "Upload PDF",
    onConfirm: async (feedback) => {
      const file = picker.files?.[0];
      if (!file) throw Error("Choose a PDF file.");
      if (
        !file.name.toLowerCase().endsWith(".pdf") ||
        (file.type && file.type !== "application/pdf")
      )
        throw Error("Only PDF files are supported.");
      if (file.size > 50 * 1024 * 1024)
        throw Error("PDF must not exceed 50 MB.");
      feedback.textContent = "Uploading PDF. Please keep this page open…";
      tracker.start();
      try {
        await sendPdfWithProgress(resource.id, file, tracker.update);
        await refresh(
          "PDF uploaded successfully. You can now publish this draft.",
        );
      } catch (error) {
        tracker.update({ phase: "error" });
        throw error;
      } finally {
        tracker.stop();
      }
    },
  });
}

// Shared author editor for upload and metadata editing.
function makeAuthorEditor(initialNames = []) {
  const wrap = node("div", "upload-field full");
  const heading = node("div", "author-heading");
  heading.append(node("span", "", "Author(s)"));
  const addButton = action("+ Add another author", () => addRow(), true);
  heading.append(addButton);
  const rows = node("div", "author-rows");
  wrap.append(heading, rows);

  function addRow(value = "") {
    if (rows.children.length >= 20) return;
    const row = node("div", "author-row");
    const input = node("input", "field-input");
    input.type = "text";
    input.maxLength = 200;
    input.placeholder = "Author full name";
    input.setAttribute("aria-label", `Author ${rows.children.length + 1}`);
    input.value = value;
    const remove = action(
      "Remove",
      () => {
        row.remove();
        addButton.disabled = false;
      },
      true,
    );
    remove.setAttribute("aria-label", "Remove this author");
    row.append(input, remove);
    rows.append(row);
    addButton.disabled = rows.children.length >= 20;
    return input;
  }
  (initialNames.length ? initialNames : [""]).forEach(addRow);
  return {
    element: wrap,
    inputs: () => [...rows.querySelectorAll("input")],
    names: () => {
      const names = [...rows.querySelectorAll("input")].map((input) =>
        input.value.trim(),
      );
      if (names.some((name) => !name && names.length > 1)) {
        throw Error("Complete each author name or remove its empty row.");
      }
      const result = names.filter(Boolean);
      if (
        new Set(result.map((name) => name.toLocaleLowerCase())).size !==
        result.length
      ) {
        throw Error("Each author must be listed only once.");
      }
      return result;
    },
  };
}

function resourceDetails(resource, isLibrarian, reload) {
  const body = node("div", "resource-detail-body");
  const status = node(
    "span",
    "manage-status " + statusOf(resource).toLowerCase(),
    statusOf(resource),
  );
  body.append(status);
  const details = node("dl", "resource-detail-grid");
  const values = [
    ["Title", resource.title],
    ["Type", resource.resource_type?.replaceAll("_", " ")],
    ["Publication year", resource.publication_year],
    ["Author(s)", (resource.authors || []).join(", ")],
    ["Publisher", resource.publisher],
    ["ISBN", resource.isbn],
    ["DOI", resource.doi],
    ["Language", resource.language],
    ["Category ID", resource.category_id],
    ["Department ID", resource.department_id],
    ["Course ID", resource.course_id],
    ["Resource ID", resource.id],
    ["Abstract", resource.abstract],
    ["Featured", resource.is_featured ? "Yes" : "No"],
  ];
  for (const [key, value] of values) {
    if (value !== null && value !== undefined && value !== "") {
      details.append(node("dt", "", key), node("dd", "", String(value)));
    }
  }
  body.append(details);
  body.append(
    node(
      "p",
      "resource-file-note",
      "PDF file status is not included in the current resource-details API. A published resource has passed the PDF requirement.",
    ),
  );
  const actions = node("div", "manage-row-actions");
  if (isLibrarian) {
    actions.append(
      action(
        "Edit Authors",
        () => {
          modal.dismiss();
          const editor = makeAuthorEditor(resource.authors || []);
          openDialog({
            heading: "Edit Resource Authors",
            explanation: resource.title,
            content: editor.element,
            confirmText: "Save Authors",
            onConfirm: async () => {
              const names = editor.names();
              await apiRequest(`/resources/${resource.id}`, {
                method: "PATCH",
                body: JSON.stringify({ authors: names }),
              });
              await reload("Author information saved.");
            },
          });
        },
        true,
      ),
    );
  }
  body.append(actions);
  const modal = openDialog({
    heading: "Resource details",
    explanation: resource.title,
    content: body,
    confirmText: "Close",
    onConfirm: async () => {},
  });
}

export async function showLibrarianResources({ user, content }) {
  const isLibrarian = user.role === "librarian";
  content.classList.add("unn-resource-management");
  const canView = isLibrarian || user.role === "admin";
  if (!canView) {
    content.append(node("p", "error-state", "Not authorized."));
    return;
  }
  const intro = node("div", "page-heading");
  intro.append(
    node("p", "eyebrow", "UNN E-LIBRARY · COLLECTION MANAGEMENT"),
    node("h1", "", "Manage Resources"),
    node(
      "p",
      "subheading",
      isLibrarian
        ? "Create a draft, upload a PDF, and publish when ready."
        : "Read-only collection overview. Resource changes are restricted to librarians.",
    ),
  );
  content.append(intro);
  const toolbar = node("div", "manage-toolbar");
  const search = node("input", "field-input");
  search.type = "search";
  search.placeholder = "Search title, author, ISBN or DOI";
  search.setAttribute("aria-label", "Search resources");
  search.maxLength = 200;
  const fieldFilter = node("select", "field-input search-field-select");
  fieldFilter.setAttribute("aria-label", "Search within");
  [
    ["all", "All fields"],
    ["title", "Title"],
    ["author", "Author"],
    ["isbn", "ISBN"],
    ["doi", "DOI"],
    ["abstract", "Abstract"],
  ].forEach(([value, label]) => {
    const option = node("option", "", label);
    option.value = value;
    fieldFilter.append(option);
  });
  fieldFilter.addEventListener("change", () => {
    offset = 0;
    load();
  });
  const searchButton = action("Search", () => {
    offset = 0;
    load();
  });
  const statusFilter = node("select", "field-input");
  [
    ["all", "All statuses"],
    ["published", "Published"],
    ["draft", "Draft"],
    ["archived", "Archived"],
  ].forEach(([v, t]) => {
    const o = node("option", "", t);
    o.value = v;
    statusFilter.append(o);
  });
  statusFilter.addEventListener("change", () => {
    offset = 0;
    load();
  });
  toolbar.append(search, fieldFilter, searchButton, statusFilter);
  if (isLibrarian)
    toolbar.append(action("+ Upload Resource", () => openUploadModal(load)));
  content.append(toolbar);
  const feedback = node("p", "manage-feedback");
  feedback.setAttribute("role", "status");
  feedback.setAttribute("aria-live", "polite");
  content.append(feedback);
  const collection = node("div", "manage-collection");
  content.append(collection);
  const pager = node("div", "pager");
  content.append(pager);
  let offset = 0;
  const limit = 25;
  search.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      offset = 0;
      load();
    }
  });
  
function deleteResource(resource) {
  openDialog({
    heading: "Permanently delete resource?",
    explanation:
      `"${resource.title}" will be permanently deleted. ` +
      "This action cannot be undone.",
    confirmText: "Delete Permanently",
    danger: true,

    onConfirm: async () => {
      await apiRequest(`/resources/${resource.id}`, {
        method: "DELETE",
      });

      await load();

      feedback.textContent =
        "Resource permanently deleted.";
    },
  });
}

  function mutate(resource, verb) {
    const prompts = {
      publish: [
        "Publish resource",
        "Make this resource available to students and lecturers?",
        "Publish",
      ],
      unpublish: [
        "Unpublish resource",
        "Move this resource back to draft status?",
        "Unpublish",
      ],
      archive: [
        "Archive resource",
        "Remove this resource from the active collection?",
        "Archive",
      ],
      unarchive: [
        "Restore resource",
        "Restore this archived resource as a draft?",
        "Restore",
      ],
    };
    const [heading, explanation, confirmText] = prompts[verb];
    openDialog({
      heading,
      explanation: `${resource.title} — ${explanation}`,
      confirmText,
      danger: verb === "archive",
      onConfirm: async (dialogFeedback) => {
        dialogFeedback.textContent = `Updating resource #${resource.id}…`;
        try {
          await apiRequest(`/resources/${resource.id}/${verb}`, {
            method: "POST",
          });
          await load();
          feedback.textContent = `Resource ${verb} succeeded.`;
        } catch (e) {
          if (verb === "publish" && /uploaded PDF/i.test(errText(e))) {
            dialogFeedback.textContent =
              "This draft has no registered PDF. Close this dialog and select “Attach PDF” on the resource before publishing.";
            throw Error("A PDF must be uploaded before publishing.");
          }
          throw e;
        }
      },
    });
  }
  async function reloadWithMessage(message) {
    await load();
    feedback.textContent = message;
  }
  async function load() {
    collection.replaceChildren();
    const tableHeader = node("div", "unn-resource-table-header");

    for (const title of [
      "Resource",
      "Author",
      "Department",
      "Status",
      "Actions",
    ]) {
      tableHeader.append(node("span", "", title));
    }

    collection.append(tableHeader);
    pager.replaceChildren();
    feedback.textContent = "Loading resources...";
    try {
      // Get department names for the resource table.
      let departments = [];

      try {
        const result = await apiRequest("/academic/departments");
        departments = Array.isArray(result)
          ? result
          : result.items || [];
      } catch {
        // Continue displaying resources if the lookup fails.
      }
      const p = new URLSearchParams({
        limit: String(limit),
        offset: String(offset),
      });
      if (search.value.trim()) {
        p.set("search", search.value.trim());
        p.set("search_field", fieldFilter.value);
      }
      const data = await apiRequest(`/resources?${p.toString()}`);
      const rows = (data.items || []).filter(
        (r) =>
          statusFilter.value === "all" ||
          statusOf(r).toLowerCase() === statusFilter.value,
      );
      feedback.textContent = `Showing ${rows.length} resources on this page · ${data.total ?? 0} total results`;
      if (!rows.length) {
        collection.append(
          node("p", "empty-state", "No resources match the selected filters."),
        );
      }
      for (const r of rows) {
        const row = node("article", "manage-resource-row");
        const info = node("div", "manage-resource-info");
        info.append(
          node("h3", "", r.title),
          node(
            "p",
            "",
            `${(r.resource_type || "resource").replaceAll("_", " ")}${r.publication_year ? " · " + r.publication_year : ""}`,
          ),
        );
        const tag = node(
          "span",
          "manage-status " + statusOf(r).toLowerCase(),
          statusOf(r),
        );
        const actions = node("div", "manage-row-actions");
        actions.append(
          action(
            "View Details",
            () => resourceDetails(r, isLibrarian, reloadWithMessage),
            true,
          ),
        );
        if (isLibrarian) {
            if (r.is_archived) {
              actions.append(
                action("Restore", () => mutate(r, "unarchive"), true),
                action("Delete", () => deleteResource(r), true),
              );
            } else if (r.is_published)

            actions.append(
              action("Unpublish", () => mutate(r, "unpublish"), true),
              action("Archive", () => mutate(r, "archive"), true),
            );
          else
            actions.append(
              action("Publish", () => mutate(r, "publish")),
              action("Archive", () => mutate(r, "archive"), true),
            );
        }
        row.append(info, tag, actions);
        const author = node(
          "span",
          "unn-resource-author",
          (r.authors || []).join(", ") || "—",
        );

        const department = departments.find(
          (d) => Number(d.id) === Number(r.department_id),
        );

        const departmentName = node(
          "span",
          "unn-resource-department",
          department?.name || "—",
        );
        
        for (const btn of actions.querySelectorAll("button")) {
          if (btn.classList.contains("unn-icon-action")) continue;

          const label = btn.textContent.trim();

          const icons = {
            "View Details": "◉",
            "Publish": "↑",
            "Unpublish": "↓",
            "Archive": "▣",
            "Restore": "↶",
            "Delete": "✕",
          };

          btn.classList.add("unn-icon-action");

          // Show the action name when hovering.
          btn.title = label;

          // Let screen readers identify the action.
          btn.setAttribute("aria-label", label);

          const icon = document.createElement("span");
          icon.className = "unn-action-icon";
          icon.setAttribute("aria-hidden", "true");
          icon.textContent = icons[label] || "•";

          const text = document.createElement("span");
          text.className = "unn-action-text";
          text.textContent = label;

          btn.replaceChildren(icon, text);
        }

        row.append(info, author, departmentName, tag, actions);
        collection.append(row);
      }
      const prev = action(
        "← Previous",
        () => {
          offset -= limit;
          load();
        },
        true,
      );
      prev.disabled = offset <= 0;
      const next = action(
        "Next →",
        () => {
          offset += limit;
          load();
        },
        true,
      );
      next.disabled = offset + limit >= (data.total || 0);
      pager.append(
        prev,
        node("span", "", `Page ${Math.floor(offset / limit) + 1}`),
        next,
      );
    } catch (e) {
      collection.append(node("p", "error-state", errText(e)));
      feedback.textContent = "Unable to load resources.";
    }
  }
  await load();
}

function openUploadModal(onComplete) {
  const backdrop = node("div", "upload-backdrop");
  const dialog = node("section", "upload-dialog");
  dialog.setAttribute("role", "dialog");
  dialog.setAttribute("aria-modal", "true");
  dialog.setAttribute("aria-labelledby", "upload-heading");
  const header = node("div", "upload-header");
  const title = node("div");
  title.append(
    node("p", "eyebrow", "LIBRARIAN WORKSPACE"),
    node("h2", "", "Upload Academic Resource"),
  );
  title.querySelector("h2").id = "upload-heading";
  const close = action("✕", dismiss, true);
  close.setAttribute("aria-label", "Close upload dialog");
  header.append(title, close);
  dialog.append(header);

  const form = node("form", "upload-form");
  const fields = node("div", "upload-fields");
  function field(label, type = "text", required = false, max) {
    const wrap = node("label", "upload-field");
    wrap.append(node("span", "", label));
    const inp = node("input", "field-input");
    inp.type = type;
    inp.required = required;
    if (max) inp.maxLength = max;
    wrap.append(inp);
    fields.append(wrap);
    return inp;
  }
  const titleInput = field("Resource title *", "text", true, 300);
  const typeLabel = node("label", "upload-field");
  typeLabel.append(node("span", "", "Resource type *"));
  const typeSelect = node("select", "field-input");
  types.forEach((t) => {
    const option = node("option", "", t.replaceAll("_", " "));
    option.value = t;
    typeSelect.append(option);
  });
  typeLabel.append(typeSelect);
  fields.append(typeLabel);
  const yearInput = field("Publication year", "number");
  yearInput.min = "1000";
  yearInput.max = "9999";
  const authorEditor = makeAuthorEditor();
  fields.append(authorEditor.element);
  const publisher = field("Publisher (optional)", "text", false, 200);
  const isbn = field("ISBN", "text", false, 20);
  const doi = field("DOI", "text", false, 100);
  const catId = field("Category ID (optional)", "number");
  catId.min = "1";
  // Academic names are shown to librarians; API IDs remain internal.
  function academicSelect(labelText) {
    const wrap = node("label", "upload-field");
    wrap.append(node("span", "", labelText));
    const select = node("select", "field-input");
    const placeholder = node("option", "", "Loading options…");
    placeholder.value = "";
    select.append(placeholder);
    wrap.append(select);
    fields.append(wrap);
    return select;
  }
  const depId = academicSelect("Department (optional)");
  const courseId = academicSelect("Course (optional)");
  function putOptions(select, rows, description) {
    select.replaceChildren();
    const empty = node("option", "", description);
    empty.value = "";
    select.append(empty);
    for (const item of rows) {
      const opt = node("option", "", item.label);
      opt.value = String(item.id);
      select.append(opt);
    }
  }
  async function loadCourses() {
    courseId.disabled = true;
    putOptions(courseId, [], "Loading courses…");
    try {
      const query = depId.value ? `?department_id=${depId.value}` : "";
      const rows = await apiRequest(`/academic/courses${query}`);
      putOptions(courseId, rows.map(x => ({id:x.id,label:`${x.course_code} — ${x.title}`})), "No course selected");
      courseId.disabled = false;
    } catch (err) {
      putOptions(courseId, [], "Courses unavailable — refresh");
    }
  }
  depId.addEventListener("change", () => void loadCourses());
  void (async () => {
    try {
      const rows = await apiRequest("/academic/departments");
      putOptions(depId, rows.map(x => ({id:x.id,label:`${x.name} (${x.code})`})), "No department selected");
      await loadCourses();
    } catch (err) {
      putOptions(depId, [], "Departments unavailable — refresh");
      putOptions(courseId, [], "Courses unavailable — refresh");
    }
  })();
  const description = node("label", "upload-field full");
  description.append(node("span", "", "Abstract / description"));
  const abstract = node("textarea", "field-input");
  abstract.maxLength = 1000;
  abstract.rows = 3;
  abstract.placeholder = "Enter a brief description of this academic resource…";
  description.append(abstract);
  fields.append(description);
  const fileLabel = node("label", "upload-field full");
  fileLabel.append(node("span", "", "Academic PDF *"));
  const file = node("input", "field-input");
  file.type = "file";
  file.accept = "application/pdf,.pdf";
  file.required = true;
  fileLabel.append(
    file,
    node("small", "", "PDF only · maximum 50 MB · stored privately"),
  );
  fields.append(fileLabel);

  const publishLabel = node("label", "upload-publish");
  const publishCheck = node("input");
  publishCheck.type = "checkbox";
  publishCheck.checked = true;
  publishLabel.append(
    publishCheck,
    node(
      "span",
      "",
      "Publish immediately after successful upload (otherwise keep as draft)",
    ),
  );
  const note = node(
    "p",
    "unn-blue-note",
    "Your PDF is uploaded to private storage. Only after the file is confirmed will this resource be published. Authorized readers receive a personalized watermark.",
  );
  const tracker = makeUploadTracker(form);
  const feedback = node("p", "form-feedback");
  feedback.setAttribute("role", "alert");
  feedback.setAttribute("aria-live", "polite");
  const buttons = node("div", "upload-footer");
  const cancel = action("Cancel", dismiss, true);
  const save = node("button", "btn-primary-alt", "Upload & Publish");
  save.type = "submit";
  buttons.append(cancel, save);
  form.append(fields, tracker.element, note, publishLabel, feedback, buttons);
  dialog.append(form);
  backdrop.append(dialog);
  document.body.append(backdrop);
  const formerFocus = document.activeElement;
  titleInput.focus();

  // Keep the initial draft ID and upload state to prevent duplicate drafts on retry.
  let createdId = null;
  let pdfRegistered = false;
  let submitting = false;
  let completed = false;
  const keyHandler = (e) => {
    if (e.key === "Escape" && !submitting) dismiss();
  };
  document.addEventListener("keydown", keyHandler);
  publishCheck.addEventListener("change", () => {
    save.textContent = publishCheck.checked
      ? "Upload & Publish"
      : "Upload as Draft";
  });
  function dismiss() {
    if (submitting) return;
    document.removeEventListener("keydown", keyHandler);
    backdrop.remove();
    formerFocus?.focus?.();
  }
  function lockInputs(locked) {
    submitting = locked;
    for (const input of form.querySelectorAll(
      "input, textarea, select, button",
    ))
      input.disabled = locked;
    save.disabled = locked;
    cancel.disabled = locked;
    close.disabled = locked;
  }
  function jumpToTracker() {
    tracker.element.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (submitting || completed) return;
    const selected = file.files?.[0];
    if (!pdfRegistered && !selected) {
      feedback.textContent = "Please choose a PDF file.";
      return;
    }
    if (!pdfRegistered && selected.size > 50 * 1024 * 1024) {
      feedback.textContent = "PDF must not exceed 50 MB.";
      return;
    }
    if (!pdfRegistered && !selected.name.toLowerCase().endsWith(".pdf")) {
      feedback.textContent = "Only PDF files are supported.";
      return;
    }
    const body = {
      title: titleInput.value.trim(),
      resource_type: typeSelect.value,
    };
    if (!body.title) {
      feedback.textContent = "Please enter a resource title.";
      return;
    }
    const add = (key, input, numeric = false) => {
      if (input.value.trim())
        body[key] = numeric ? Number(input.value) : input.value.trim();
    };
    try {
      body.authors = authorEditor.names();
    } catch (error) {
      feedback.textContent = error.message;
      return;
    }
    add("publication_year", yearInput, true);
    add("publisher", publisher);
    add("isbn", isbn);
    add("doi", doi);
    add("category_id", catId, true);
    add("department_id", depId, true);
    add("course_id", courseId, true);
    add("abstract", abstract);

    lockInputs(true);
    feedback.textContent = "";
    tracker.start();
    jumpToTracker();
    try {
      if (!createdId) {
        tracker.update({ phase: "draft" });
        const created = await apiRequest("/resources", {
          method: "POST",
          body: JSON.stringify(body),
        });
        createdId = created.id;
      }
      if (!pdfRegistered) {
        await sendPdfWithProgress(createdId, selected, tracker.update);
        pdfRegistered = true;
      }
      if (publishCheck.checked) {
        tracker.update({ phase: "publish" });
        await apiRequest(`/resources/${createdId}/publish`, { method: "POST" });
      }
      completed = true;
      tracker.update({ phase: "complete" });
      feedback.textContent = publishCheck.checked
        ? `Resource #${createdId} uploaded and published successfully.`
        : `Resource #${createdId} uploaded successfully and saved as a draft.`;
      save.textContent = "Completed";
      try {
        await onComplete();
      } catch (refreshError) {
        feedback.textContent +=
          " Refresh the resource list to see the updated status.";
      }
      cancel.textContent = "Close";
      // Keep success visible so the librarian can explain the completion state.
    } catch (error) {
      tracker.update({ phase: "error" });
      feedback.textContent = `${errText(error)}${
        createdId
          ? ` Draft #${createdId} already exists. You can retry from this dialog without creating another resource.`
          : ""
      }`;
      save.textContent = pdfRegistered
        ? publishCheck.checked
          ? "Retry Publishing"
          : "Finish"
        : createdId
          ? "Retry PDF Upload"
          : "Try Again";
    } finally {
      tracker.stop();
      lockInputs(false);
      if (completed) {
        save.disabled = true;
        file.disabled = true;
        publishCheck.disabled = true;
      }
    }
  });
}
