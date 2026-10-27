import { showLibrarianResources } from "./librarian.js";
import { apiRequest, API_BASE, getToken } from "./api.js";
import { getCurrentUser, requireLogin, logout } from "./auth.js";
import { makeBookmarkControl, showMyLibrary } from './bookmarks.js';
import { showResourceRequests } from './resource-requests.js';
import { showCourseReadingLists } from './course-reading-lists.js';
import { showCasNotifications, refreshCasBadge } from "./cas-notifications.js";
import { showProfileSettings } from "./profile-settings.js";
import { showLibrarianDashboard } from "./librarian-dashboard.js";
import { installSelectEnhancer } from "./select-enhancer.js";
import { showLibrarianRequestsPage } from "./librarian-requests-page.js";
import { showLibrarianReportsPage } from "./librarian-reports-page.js";
import { openReportResourceIssue } from "./report-resource-issue.js";
import { showReadingStatistics } from "./reading-statistics.js";
import { showAdminDashboard } from "./admin-dashboard.js";
import { showAdminUserManagement } from "./admin-user-management.js";
import { showLibraryAnalytics } from "./library-analytics.js";
import { showAdminNotificationsManagement } from "./admin-notifications-management.js";

const $ = (id) => document.getElementById(id);
const el = (tag, cls = "", txt = "") => {
  const x = document.createElement(tag);
  if (cls) x.className = cls;
  if (txt !== undefined) x.textContent = txt;
  return x;
};
const roles = {
  student: [
    ["dashboard", "Dashboard", "▦"],
    ["library", "Library & Discovery", "⌕"],
    ["recommendations", "For You", "✦"],
    ["bookmarks", "My Library", "☆"],
    ["history", "Reading History", "◷"],
    ["statistics", "Reading Statistics", "▥"],
    ["reading-lists", "Course Reading Lists", "☷"],
    ["requests", "Resource Requests", "✉"],
    ["notifications", "Notifications", "♧"],
    ["profile", "My Profile", "◉"],
  ],
  lecturer: [
    ["dashboard", "Dashboard", "▦"],
    ["library", "Library & Discovery", "⌕"],
    ["recommendations", "For You", "✦"],
    ["bookmarks", "My Library", "☆"],
    ["history", "Reading History", "◷"],
    ["reading-lists", "Course Reading Lists", "☷"],
    ["requests", "Resource Requests", "✉"],
    ["notifications", "Notifications", "♧"],
    ["profile", "My Profile", "◉"],
  ],
  librarian: [
    ["dashboard", "Dashboard", "▦"],
    ["resources-admin", "Manage Resources", "▤"],
    ["library", "Browse Library", "⌕"],
    ["reading-lists", "Reading Lists", "☷"],
    ["requests", "Process Requests", "✉"],
    ["reports", "Broken Resource Reports", "⚑"],
    ["notifications", "Notifications", "♧"],
    ["profile", "My Profile", "◉"],
  ],
  admin: [
    ["dashboard", "Dashboard", "▦"],
    ["users", "User Management", "♙"],
    ["analytics", "Library Analytics", "▥"],
    ["notifications-admin", "Notifications Management", "✉"],
    ["resources-admin", "Resources", "▤"],
    ["library", "Browse Library", "⌕"],
    ["notifications", "Notifications", "♧"],
    ["profile", "My Profile", "◉"],
  ],
};
const state = {
  user: null,
  page: "dashboard",
  busy: false,
  pdfUrls: new Set(),
};
const pageNames = {
  dashboard: "Dashboard",
  library: "Library & Discovery",
  recommendations: "Recommended for You",
  bookmarks: "My Library",
  analytics: "Library Analytics",
  history: "Reading History",
  statistics: "Reading Statistics",
  "reading-lists": "Course Reading Lists",
  requests: "Resource Requests",
  notifications: "Notifications",
  "notifications-admin": "Notifications Management",
  profile: "My Profile",
  "resources-admin": "Manage Resources",
  reports: "Broken Resource Reports",
  users: "User Management",
};
function message(txt, kind = "info") {
  const a = el("div", `notice ${kind}`, txt);
  $("content").prepend(a);
  if (kind === "error") a.setAttribute("role", "alert");
  return a;
}
function loading() {
  $("content").replaceChildren(
    el("div", "empty-state", "Loading your library data…"),
  );
}
function heading(title, desc) {
  const wrap = el("div", "page-heading");
  wrap.append(el("h1", "", title), el("p", "subheading", desc));
  $("content").append(wrap);
}
function panel(title) {
  const s = el("section", "data-panel");
  if (title) s.append(el("h2", "panel-heading", title));
  $("content").append(s);
  return s;
}
function button(text, fn, className = "btn-primary-alt") {
  const b = el("button", className, text);
  b.type = "button";
  b.addEventListener("click", fn);
  return b;
}
function empty(parent, text) {
  parent.append(el("p", "empty-state", text));
}
function error(parent, e) {
  const x = el("p", "error-state", e.message || String(e));
  x.setAttribute("role", "alert");
  parent.append(x);
}
function asItems(data) {
  if (Array.isArray(data)) return data;
  return (
    data?.items ||
    data?.results ||
    data?.resources ||
    data?.reading_lists ||
    data?.bookmarks ||
    data?.notifications ||
    data?.requests ||
    data?.users ||
    []
  );
}
function textOf(v) {
  return typeof v === "string" ? v : String(v ?? "");
}
function resourceId(r) {
  return r.resource_id ?? r.resource?.id ?? r.id;
}
function resourceOf(r) {
  return r.resource || r;
}
function input(placeholder, type = "search") {
  const x = el("input", "field-input");
  x.placeholder = placeholder;
  x.type = type;
  return x;
}
function pill(text) {
  return el("span", "pill", text || "Resource");
}
function makeCard(r, controls = true) {
  const o = resourceOf(r),
    c = el("article", "resource-card-v2");
  c.append(
    pill((o.resource_type || "Academic resource").replaceAll("_", " ")),
    el("h3", "", o.title || `Resource #${resourceId(r)}`),
  );
  c.append(
    el(
      "p",
      "card-abstract",
      (
        o.abstract ||
        o.description ||
        "View this resource in the UNN academic library."
      ).slice(0, 230),
    ),
  );
  const meta = el(
    "p",
    "card-meta",
    [o.publication_year, o.publisher].filter(Boolean).join(" · "),
  );
  c.append(meta);
  if (controls && resourceId(r)) {
    const actions = el("div", "card-actions");
    actions.append(button("Read PDF", () => openPdf(resourceId(r))));
    actions.append(
      button("Details", () => showDetails(resourceId(r)), "btn-quiet"),
    );
    actions.append(makeBookmarkControl(resourceId(r)));
    c.append(actions);
  }
  return c;
}
async function openPdf(id) {
  const readerUrl = new URL("./reader.html", window.location.href);
  readerUrl.searchParams.set("resource", String(id));
  const tab = window.open(readerUrl.href, "_blank");
  if (!tab) message("Allow pop-ups to open the protected reader.", "error");
}

async function showDetails(id) {
  $("content").replaceChildren();
  heading(
    "Resource Details",
    "Verified academic resource information and protected reading access.",
  );
  const p = panel("Resource information");
  try {
    const r = await apiRequest(`/resources/${encodeURIComponent(id)}`);
    p.append(makeCard(r, false));
    const d = el("dl", "details-grid");
    for (const [k, v] of [
      [
        "Author(s)",
        (r.authors || []).map((a) => a.author_name || a.name).join(", "),
      ],
      ["Type", r.resource_type],
      ["Year", r.publication_year],
      ["Publisher", r.publisher],
      ["ISBN", r.isbn],
      ["DOI", r.doi],
      ["Language", r.language],
    ]) {
      if (v) {
        d.append(el("dt", "", k), el("dd", "", textOf(v)));
      }
    }
    p.append(d);
    p.append(button("Read protected PDF", () => openPdf(id)));
    p.append(makeBookmarkControl(id));
    if (
      state.user.role === "student" ||
      state.user.role === "lecturer"
    ) {
      p.append(
        button(
          "Report an Issue",
          () => openReportResourceIssue(r),
          "btn-quiet unn-report-issue-button",
        ),
      );
    }
  } catch (e) {
    error(p, e);
  }
  p.append(button("← Back to Library", () => navigate("library"), "btn-quiet"));
}
async function getResources(extra = {}) {
  const p = new URLSearchParams({ limit: "24", offset: "0", ...extra });
  return apiRequest(`/resources?${p}`);
}
async function library() {
  heading(
    "Library & Discovery",
    "Search books, journals and academic publications. Open protected, personalized PDFs securely.",
  );
  const p = panel();
  const form = el("form", "search-form");
  const q = input("Search academic resources");
  const filter = el("select", "field-input search-field-select");
  filter.setAttribute("aria-label", "Search within");
  for (const [v, label] of [
    ["all", "All fields"],
    ["title", "Title"],
    ["author", "Author"],
    ["isbn", "ISBN"],
    ["doi", "DOI"],
    ["abstract", "Abstract"],
  ]) {
    const opt = el("option", "", label);
    opt.value = v;
    filter.append(opt);
  }
  const search = el("button", "btn-primary-alt", "Search");
  search.type = "submit";
  form.append(q, filter, search);
  p.append(form);
  const stats = el("p", "results-count");
  p.append(stats);
  const cards = el("div", "resource-grid-v2");
  p.append(cards);
  const pager = el("div", "pager");
  p.append(pager);
  let offset = 0;
  const limit = 24;
  async function fetchPage() {
    cards.replaceChildren();
    pager.replaceChildren();
    stats.textContent = "Loading results…";
    try {
      const params = { limit: String(limit), offset: String(offset) };
      if (q.value.trim()) {
        params.search = q.value.trim();
        params.search_field = filter.value;
      }
      const result = await getResources(params);
      const list = asItems(result).filter(
        (r) => r.is_published !== false && !r.is_archived,
      );
      stats.textContent = `${result.total ?? list.length} resources found`;
      if (!list.length)
        empty(cards, "No published resources matched your search.");
      else list.forEach((r) => cards.append(makeCard(r)));
      const total = Number(result.total ?? list.length);
      const prev = button(
        "← Previous",
        () => {
          offset = Math.max(0, offset - limit);
          fetchPage();
        },
        "btn-quiet",
      );
      prev.disabled = offset === 0;
      const next = button(
        "Next →",
        () => {
          offset += limit;
          fetchPage();
        },
        "btn-quiet",
      );
      next.disabled = offset + limit >= total;
      pager.append(
        prev,
        el("span", "", `Page ${Math.floor(offset / limit) + 1}`),
        next,
      );
    } catch (e) {
      stats.textContent = "";
      error(cards, e);
    }
  }
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    offset = 0;
    fetchPage();
  });
  filter.addEventListener("change", () => {
    offset = 0;
    fetchPage();
  });
  await fetchPage();
}
async function history() {
  heading(
    "Reading History",
    "Recently accessed resources, recorded when you open a protected PDF.",
  );
  const p = panel("Your reading activity");
  try {
    const data = await apiRequest("/reading-history");
    const entries = asItems(data);
    if (!entries.length) {
      empty(p, "No reading history yet. Open a protected PDF to begin.");
      return;
    }
    const grid = el("div", "history-list");
    p.append(grid);
    const ids = [...new Set(entries.map(resourceId).filter(Boolean))];
    const details = new Map();
    await Promise.all(
      ids.map(async (id) => {
        try {
          details.set(
            id,
            await apiRequest(`/resources/${encodeURIComponent(id)}`),
          );
        } catch (e) {
          details.set(id, null);
        }
      }),
    );
    for (const entry of entries) {
      const id = resourceId(entry);
      const resource = details.get(id);
      const card = el("article", "history-entry");
      card.append(
        pill(
          resource?.resource_type?.replaceAll("_", " ") || "Academic resource",
        ),
      );
      card.append(
        el(
          "h3",
          "",
          resource?.title || `Resource #${id || "unknown"} (unavailable)`,
        ),
      );
      if (resource?.abstract)
        card.append(el("p", "card-abstract", resource.abstract.slice(0, 220)));
      const last = entry.last_read_at || entry.started_at || entry.created_at;
      if (last) {
        const d = new Date(last);
        card.append(
          el(
            "p",
            "card-meta",
            `Last accessed: ${Number.isNaN(d.getTime()) ? String(last) : d.toLocaleString()}`,
          ),
        );
      }
      const progressLabel = el(
        "p",
        "history-progress-label",
        "Loading actual reading progress…",
      );
      card.append(progressLabel);
      if (id) {
        apiRequest(`/reading-progress/${encodeURIComponent(id)}`)
          .then((progress) => {
            if (progress.current_page && progress.total_pages) {
              const pct = Math.round(
                (progress.current_page / progress.total_pages) * 100,
              );
              progressLabel.textContent = `Page ${progress.current_page} of ${progress.total_pages} · ${pct}% reached`;
              const bar = el("div", "reading-progress-track");
              const fill = el("div", "reading-progress-fill");
              fill.style.width = `${pct}%`;
              bar.append(fill);
              progressLabel.after(bar);
            } else progressLabel.textContent = "No page progress saved yet.";
          })
          .catch(() => {
            progressLabel.textContent = "Page progress unavailable.";
          });
      } else progressLabel.textContent = "Page progress unavailable.";
      if (resource) {
        const buttons = el("div", "card-actions");
        buttons.append(
          button("Read PDF", () => openPdf(id)),
          button("Details", () => showDetails(id), "btn-quiet"),
        );
        card.append(buttons);
      }
      grid.append(card);
    }
  } catch (e) {
    if (e.status === 401 || e.status === 403) {
      logout();
      return;
    }
    error(p, e);
  }
}
async function listSection(
  title,
  desc,
  endpoint,
  { format = "resources" } = {},
) {
  heading(title, desc);
  const p = panel();
  try {
    const data = await apiRequest(endpoint);
    const items = asItems(data);
    if (!items.length) {
      empty(p, "Nothing here yet.");
      return;
    }
    const grid = el(
      "div",
      format === "resources" ? "resource-grid-v2" : "stack-list",
    );
    for (const item of items) {
      if (format === "resources") grid.append(makeCard(item));
      else {
        const c = el("article", "list-record");
        const obj = item.resource || item;
        c.append(
          el(
            "h3",
            "",
            obj.title ||
              item.name ||
              item.message ||
              item.subject ||
              `Item #${item.id || ""}`,
          ),
          el(
            "p",
            "",
            item.description ||
              item.body ||
              item.status ||
              item.created_at ||
              "",
          ),
        );
        grid.append(c);
      }
    }
    p.append(grid);
  } catch (e) {
    error(p, e);
  }
}
async function home() {
  heading(
    `Welcome back, ${(state.user.full_name || "Member").split(" ")[0]}!`,
    "Your academic resources, securely available in one place.",
  );
  const hero = el("section", "hero-panel");
  hero.append(
    el("div", "eyebrow", "YOUR UNN ACADEMIC WORKSPACE"),
    el("h2", "", "Knowledge without boundaries."),
    el(
      "p",
      "",
      "Discover trusted materials, continue reading, and explore new scholarship.",
    ),
  );
  hero.append(button("Browse academic library →", () => navigate("library")));
  $("content").append(hero);
  const actions = panel("Quick access");
  const grid = el("div", "shortcut-grid");
  const nav = roles[state.user.role] || roles.student;
  for (const [id, label, icon] of nav
    .filter(([id]) => !["dashboard", "profile"].includes(id))
    .slice(0, 6)) {
    const card = button(`${icon}   ${label}`, () => navigate(id), "shortcut");
    grid.append(card);
  }
  actions.append(grid);
  const recent = panel("Recently published resources");
  try {
    const data = await getResources({ limit: "6", offset: "0" });
    const items = asItems(data)
      .filter((r) => r.is_published !== false && !r.is_archived)
      .slice(0, 6);
    const g = el("div", "resource-grid-v2");
    items.forEach((r) => g.append(makeCard(r)));
    if (!items.length)
      empty(recent, "No published resources are available yet.");
    else recent.append(g);
  } catch (e) {
    error(recent, e);
  }
}
async function requests() {
  if (state.user.role === "librarian") return librarianRequests();
  heading(
    "Resource Requests",
    "Request academic materials and check the status of previous requests.",
  );
  const formPanel = panel("Submit a resource request");
  const f = el("form", "request-form");
  const title = input("Title of the requested resource", "text");
  title.required = true;
  title.maxLength = 255;
  const author = input("Author (if known)", "text");
  const notes = el("textarea", "field-input");
  notes.placeholder = "Additional details (optional)";
  const btn = el("button", "btn-primary-alt", "Submit Request");
  btn.type = "submit";
  const status = el("p", "form-feedback");
  f.append(title, author, notes, btn, status);
  formPanel.append(f);
  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    btn.disabled = true;
    status.textContent = "Submitting…";
    try {
      await apiRequest("/requests", {
        method: "POST",
        body: JSON.stringify({
          title: title.value.trim(),
          author: author.value.trim() || null,
          description: notes.value.trim() || null,
        }),
      });
      status.textContent = "Request submitted.";
      f.reset();
      navigate("requests");
    } catch (err) {
      status.textContent = `Could not submit: ${err.message}`;
    } finally {
      btn.disabled = false;
    }
  });
  const p = panel("Request history");
  try {
    const data = await apiRequest("/requests");
    const rows = asItems(data);
    if (!rows.length) empty(p, "No requests submitted yet.");
    else
      for (const r of rows) {
        const c = el("div", "list-record");
        c.append(
          el("h3", "", r.title || r.resource_title || `Request #${r.id}`),
          pill(r.status),
          el("p", "", r.description || r.reason || ""),
        );
        p.append(c);
      }
  } catch (e) {
    error(p, e);
  }
}
async function librarianRequests() {
  heading(
    "Process Resource Requests",
    "Review academic-resource requests submitted by students and lecturers.",
  );
  const p = panel("Incoming requests");
  try {
    const data = await apiRequest("/requests");
    const rows = asItems(data);
    if (!rows.length) {
      empty(p, "No incoming requests.");
      return;
    }
    const list = el("div", "stack-list");
    for (const r of rows) {
      const card = el("article", "list-record");
      card.append(
        el("h3", "", r.title || r.resource_title || `Request #${r.id}`),
        pill(r.status || "Submitted"),
        el("p", "", r.description || r.reason || r.author || ""),
      );
      list.append(card);
    }
    p.append(list);
  } catch (e) {
    error(p, e);
  }
}
async function notices() {
  heading(
    "Notifications",
    "Updates about resources, reading lists and library requests.",
  );
  const p = panel("Your notifications");
  try {
    const d = await apiRequest("/notifications");
    const rows = asItems(d);
    if (!rows.length) empty(p, "No notifications yet.");
    for (const x of rows) {
      const c = el("article", "list-record");
      c.append(
        el("h3", "", x.title || "Library notification"),
        el("p", "", x.message || x.body || ""),
      );
      if (!x.is_read && x.id)
        c.append(
          button(
            "Mark as read",
            async () => {
              try {
                await apiRequest(`/notifications/${x.id}/read`, {
                  method: "PATCH",
                });
                navigate("notifications");
              } catch (e) {
                message(e.message, "error");
              }
            },
            "btn-quiet",
          ),
        );
      p.append(c);
    }
  } catch (e) {
    error(p, e);
  }
}
function profile() {
  heading(
    "Profile & Account Settings",
    "Your account details are provided by UNN E-Library.",
  );
  const p = panel("Personal information");
  const grid = el("dl", "details-grid");
  for (const [k, v] of [
    ["Full Name", state.user.full_name],
    ["Email", state.user.email],
    ["Role", state.user.role],
    ["Matriculation Number", state.user.matric_number],
    ["Staff ID", state.user.staff_id],
    ["Academic Level", state.user.academic_level],
    ["Department ID", state.user.department_id],
  ])
    if (v !== undefined && v !== null && v !== "") {
      grid.append(el("dt", "", k), el("dd", "", textOf(v)));
    }
  p.append(grid);
  p.append(button("Log out", logout, "btn-quiet"));
}
async function manageUsers() {
  heading("User Management", "Administrator-only account management.");
  if (state.user.role !== "admin") {
    message("You are not authorized for this screen.", "error");
    return;
  }
  const p = panel("User accounts");
  try {
    const d = await apiRequest("/admin/users");
    const users = asItems(d);
    if (!users.length) empty(p, "No accounts returned.");
    for (const u of users) {
      const c = el("article", "list-record");
      c.append(
        el("h3", "", u.full_name || u.email),
        el(
          "p",
          "",
          `${u.email} · ${u.role} · ${u.is_active ? "Active" : "Inactive"}`,
        ),
      );
      p.append(c);
    }
  } catch (e) {
    error(p, e);
  }
}
async function manageResources() {
  await showLibrarianResources({ user: state.user, content: $("content") });
}
function navigate(page) {
  if (page === "dashboard" && !location.hash) {
    void render("dashboard");
    return;
  }
  if (location.hash === `#${page}`) {
    void render(page);
  } else {
    location.hash = `#${page}`;
  }
}
function sidebar() {
  const s = $("sidebar");
  s.replaceChildren();
  const brand = el("div", "sidebar-brand");
  const logo = el("span", "sidebar-logo", "UNN");
  const close = button("×", () => s.classList.remove("open"), "sidebar-close");
  close.setAttribute("aria-label", "Close navigation");
  brand.append(logo, close);
  s.append(
    brand,
    el("p", "nav-label", `${state.user.role.toUpperCase()} SPACE`),
  );
  for (const [id, label, icon] of roles[state.user.role] || roles.student) {
    const link = el("a", `nav-item ${state.page === id ? "active" : ""}`);
    link.href = `#${id}`;
    link.addEventListener("click", (event) => {
      if (location.hash === `#${id}`) {
        event.preventDefault();
        void render(id);
      }
    });
    link.append(el("span", "nav-symbol", icon), el("span", "", label));
    if (state.page === id) link.setAttribute("aria-current", "page");
    s.append(link);
  }
  const foot = el("div", "sidebar-footer");
  foot.append(button("↪ Log Out", logout, "nav-item logout"));
  s.append(foot);
  void refreshCasBadge();
}
async function render(name) {
  if (!state.user) return;
  const permitted = (roles[state.user.role] || roles.student).map((x) => x[0]);
  const page = permitted.includes(name) ? name : "dashboard";
  state.page = page;
  sidebar();
  $("content").replaceChildren();
  $("content").classList.remove("unn-resource-management");
  $("page-title").textContent = pageNames[page] || "Dashboard";
  $("profile-name").textContent = state.user.full_name || "Member";
  $("profile-initial").textContent = (state.user.full_name || "U")
    .charAt(0)
    .toUpperCase();
  $("role-label").textContent = state.user.role;
  try {
    switch (page) {
      
      case "dashboard":
        if (state.user.role === "librarian") {
          await showLibrarianDashboard({
            content: $("content"),
          });
        } else if (state.user.role === "admin") {
          await showAdminDashboard({
            content: $("content"),
            user: state.user,
          });
        } else {
          await home();
        }
        break;
      case "library":
        await library();
        break;
      case "recommendations":
        await listSection(
          "Recommended for You",
          "Personalized academic suggestions from your learning interests.",
          "/recommendations/me",
        );
        break;
      case "bookmarks":
        await showMyLibrary({ content: $("content"), openPdf, showDetails });
        break;
      case "history":
        await history();
        break;
      case "statistics":
        await showReadingStatistics({
          content: $("content"),
          openPdf,
          showDetails,
        });
        break;
      case "reading-lists":
        await showCourseReadingLists({ user: state.user, content: $("content") });
        break;
      case "requests":
        if (state.user.role === "librarian") {
          await showLibrarianRequestsPage({
            content: $("content"),
          });
        } else {
          await showResourceRequests({
            user: state.user,
            content: $("content"),
          });
        }
        break;
      case "notifications-admin":
        await showAdminNotificationsManagement({
          content: $("content"),
          user: state.user,
        });
        break;
      case "notifications":
        await showCasNotifications({
          content: $("content"),
          onOpenResource: (id) => showDetails(id),
        });
        break;
      case "profile":
        await showProfileSettings({
          content: $("content"),
          user: state.user,
          onSaved: (updatedUser) => {
            state.user = updatedUser;
            $("profile-name").textContent = updatedUser.full_name;
            $("profile-initial").textContent =
              updatedUser.full_name.charAt(0).toUpperCase();
          },
        });
        break;
      case "users":
        await showAdminUserManagement({
          content: $("content"),
          user: state.user,
        });
        break;
      case "analytics":
        await showLibraryAnalytics({
          content: $("content"),
          user: state.user,
        });
        break;
      case "resources-admin":
        await manageResources();
        break;
      case "reports":
        if (state.user.role === "librarian") {
          await showLibrarianReportsPage({
            content: $("content"),
          });
        } else {
          await listSection(
            "Broken Resource Reports",
            "Reported problems and their current statuses.",
            "/reports",
            { format: "list" },
          );
        }
        break;
      default:
        await home();
    }
  } catch (e) {
    if (e.status === 401 || e.status === 403) {
      logout();
      return;
    }
    message(e.message, "error");
  }
  document.getElementById("sidebar")?.classList.remove("open");
}
async function boot() {
  if (!requireLogin()) return;
  try {
    state.user = await getCurrentUser();
    installSelectEnhancer();
    if (!roles[state.user.role])
      throw Error("Your account role is not recognized.");
    const route = () =>
      render(decodeURIComponent(location.hash.replace("#", "") || "dashboard"));
    window.addEventListener("hashchange", route);
    $("menu-toggle").addEventListener("click", () =>
      $("sidebar").classList.toggle("open"),
    );
    window.addEventListener("pagehide", () => {
      for (const u of state.pdfUrls) URL.revokeObjectURL(u);
    });
    await route();
  } catch (e) {
    if (e.status === 401 || e.status === 403) {
      logout();
      return;
    }
    $("content").replaceChildren();
    message(e.message, "error");
  }
}
boot();
