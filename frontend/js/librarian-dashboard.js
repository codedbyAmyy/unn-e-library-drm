import { apiRequest } from "./api.js";

const node = (tag, className = "", text = "") => {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = text;
  return element;
};
const list = (data) => (Array.isArray(data) ? data : data?.items || []);
const count = (data) => Number(data?.total ?? list(data).length);
const pretty = (value) =>
  String(value || "other")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
const safeDate = (value) =>
  value
    ? new Date(value).toLocaleDateString(undefined, {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : "—";
const route = (page) => {
  location.hash = `#${page}`;
  window.dispatchEvent(new HashChangeEvent("hashchange"));
};

function card(label, value, note, icon) {
  const c = node("article", "ld-stat");
  const top = node("div", "ld-stat-top");
  top.append(
    node("span", "ld-stat-label", label),
    node("span", "ld-stat-icon", icon),
  );
  c.append(
    top,
    node("strong", "ld-stat-value", value),
    node("small", "ld-stat-note", note),
  );
  return c;
}
function block(title, moreLabel, morePage) {
  const p = node("section", "ld-panel");
  const h = node("div", "ld-panel-header");
  h.append(node("h2", "", title));
  if (morePage) {
    const b = node("button", "ld-link", moreLabel);
    b.type = "button";
    b.addEventListener("click", () => route(morePage));
    h.append(b);
  }
  p.append(h);
  return p;
}
function loadingCard(text) {
  return node("p", "ld-muted", text);
}
async function safeGet(endpoint) {
  try {
    return { data: await apiRequest(endpoint), error: null };
  } catch (error) {
    return { data: null, error };
  }
}
export async function showLibrarianDashboard({ content }) {
  const root = node("div", "ld-root");
  const title = node("h1", "ld-title", "Dashboard");
  const subtitle = node(
    "p",
    "ld-subtitle",
    "Manage library resources, support readers, and monitor library activity.",
  );
  root.append(title, subtitle);
  const stats = node("div", "ld-stats");
  root.append(stats);
  const mid = node("div", "ld-columns");
  root.append(mid);
  const bottom = node("div", "ld-columns ld-columns-bottom");
  root.append(bottom);
  content.append(root);
  stats.append(
    card("Total Resources", "…", "Loading catalogue", "▤"),
    card("Pending Requests", "…", "Loading requests", "◷"),
    card("New Uploads This Month", "…", "Loading activity", "⇧"),
    card("Open Resource Reports", "…", "Loading reports", "⚑"),
  );

  const results = await Promise.all([
    safeGet("/resources?limit=100&offset=0"),
    safeGet("/requests?status=pending&limit=1&offset=0"),
    safeGet("/reports?status=open&limit=1&offset=0"),
    safeGet("/requests?limit=5&offset=0"),
    safeGet("/resources?limit=6&offset=0"),
  ]);
  if (!root.isConnected) return;
  const [resources, pending, reports, recentRequests, recentResources] =
    results;
  const resourceItems = list(resources.data);
  const total = resources.error ? "—" : count(resources.data);
  const pendingCount = pending.error ? "—" : count(pending.data);
  const reportCount = reports.error ? "—" : count(reports.data);
  const uploadedRecently = resourceItems.filter((r) => {
    if (!r.created_at) return false;
    const d = new Date(r.created_at),
      now = new Date();
    return (
      d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth()
    );
  }).length;
  // ResourceResponse may omit created_at; don't invent a monthly count.
  const monthlyValue = resourceItems.some((r) => r.created_at)
    ? resources.data?.total > 100
      ? "—"
      : String(uploadedRecently)
    : "—";
  stats.replaceChildren();
  stats.append(
    card(
      "Total Resources",
      String(total),
      "All accessible catalogue records",
      "▤",
    ),
    card(
      "Pending Requests",
      String(pendingCount),
      "Awaiting librarian review",
      "◷",
    ),
    card(
      "New Uploads This Month",
      monthlyValue,
      monthlyValue === "—"
        ? "Not available from this API"
        : "Created this calendar month",
      "⇧",
    ),
    card(
      "Open Resource Reports",
      String(reportCount),
      "Unresolved reported issues",
      "⚑",
    ),
  );
  const overview = block("Resource Overview");
  overview.append(
    node(
      "p",
      "ld-muted",
      "Distribution by resource type · showing the current catalogue page",
    ),
  );
  if (resources.error)
    overview.append(node("p", "ld-error", "Could not load resource overview."));
  else if (!resourceItems.length)
    overview.append(loadingCard("No resources found."));
  else {
    const counts = new Map();
    for (const r of resourceItems)
      counts.set(r.resource_type, (counts.get(r.resource_type) || 0) + 1);
    for (const [type, n] of [...counts]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)) {
      const line = node("div", "ld-barline");
      const label = node("span", "", pretty(type));
      const track = node("div", "ld-track");
      const fill = node("div", "ld-fill");
      fill.style.width = `${Math.round((n / resourceItems.length) * 100)}%`;
      track.append(fill);
      line.append(label, track, node("span", "ld-barcount", String(n)));
      overview.append(line);
    }
    if (count(resources.data) > 100)
      overview.append(
        node(
          "small",
          "ld-muted",
          "Type distribution is limited to the first 100 records.",
        ),
      );
  }
  const actions = block("Quick Actions");
  const grid = node("div", "ld-actiongrid");
  for (const [name, page, icon] of [
    ["Manage Resources", "resources-admin", "▤"],
    ["Manage Reading Lists", "reading-lists", "☷"],
    ["Process Requests", "requests", "✉"],
    ["Review Reports", "reports", "⚑"],
  ]) {
    const btn = node("button", "ld-action", `${icon}  ${name}`);
    btn.type = "button";
    btn.addEventListener("click", () => route(page));
    grid.append(btn);
  }
  actions.append(grid);
  mid.append(overview, actions);
  const requestsPanel = block(
    "Recent Resource Requests",
    "View all requests →",
    "requests",
  );
  if (recentRequests.error)
    requestsPanel.append(node("p", "ld-error", "Could not load requests."));
  else if (!list(recentRequests.data).length)
    requestsPanel.append(loadingCard("No resource requests yet."));
  else {
    const table = node("div", "ld-table");
    const th = node("div", "ld-tr ld-th");
    ["Requested resource", "Submitted", "Status"].forEach((s) =>
      th.append(node("span", "", s)),
    );
    table.append(th);
    list(recentRequests.data).forEach((r) => {
      const tr = node("div", "ld-tr");
      tr.append(
        node("span", "ld-primary", r.title || "Untitled request"),
        node("span", "", safeDate(r.created_at)),
        node(
          "span",
          `ld-pill ld-${r.status || "pending"}`,
          pretty(r.status || "pending"),
        ),
      );
      table.append(tr);
    });
    requestsPanel.append(table);
  }
  const recentPanel = block(
    "Recently Added Resources",
    "View all →",
    "resources-admin",
  );
  if (recentResources.error)
    recentPanel.append(node("p", "ld-error", "Could not load resources."));
  else if (!list(recentResources.data).length)
    recentPanel.append(loadingCard("No resources yet."));
  else {
    const table = node("div", "ld-table");
    const th = node("div", "ld-tr ld-th");
    ["Resource", "Type", "Status"].forEach((s) =>
      th.append(node("span", "", s)),
    );
    table.append(th);
    list(recentResources.data).forEach((r) => {
      const tr = node("div", "ld-tr");
      const st = r.is_archived
        ? "Archived"
        : r.is_published
          ? "Published"
          : "Draft";
      tr.append(
        node("span", "ld-primary", r.title || "Untitled resource"),
        node("span", "", pretty(r.resource_type)),
        node("span", `ld-pill ld-${st.toLowerCase()}`, st),
      );
      table.append(tr);
    });
    recentPanel.append(table);
  }
  bottom.append(requestsPanel, recentPanel);
  if (results.every((x) => x.error))
    root.prepend(
      node(
        "p",
        "ld-error",
        "Dashboard data could not be loaded. Check that FastAPI is running and your login is valid.",
      ),
    );
}
