import { apiRequest } from "./api.js";

const make = (tag, cls = "", text = "") => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  node.textContent = text;
  return node;
};
const button = (label, callback, style = "") => {
  const b = make("button", `anm-btn ${style}`, label);
  b.type = "button";
  b.addEventListener("click", callback);
  return b;
};
const pretty = value => (value || "unknown").replaceAll("_", " ").replace(/\b\w/g, m => m.toUpperCase());
const formatDate = value => value ? new Date(value).toLocaleString() : "—";

export async function showAdminNotificationsManagement({ content, user }) {
  content.replaceChildren();
  if (user?.role !== "admin") {
    content.append(make("p", "anm-error", "Administrator access required."));
    return;
  }
  const root = make("div", "anm-page");
  content.append(root);
  const header = make("div", "anm-heading");
  const heading = make("div");
  heading.append(make("p", "anm-eyebrow", "ADMINISTRATION / COMMUNICATION"), make("h1", "", "Notifications Management"), make("p", "anm-muted", "Send in-app announcements and review notification records."));
  header.append(heading);
  const reload = button("Refresh data", () => refresh());
  header.append(reload);
  root.append(header);
  const notice = make("p", "anm-feedback");
  notice.setAttribute("role", "status");
  root.append(notice);

  const stats = make("div", "anm-stats");
  root.append(stats);
  const layout = make("div", "anm-layout");
  root.append(layout);
  const compose = make("section", "anm-panel");
  compose.append(make("h2", "", "New in-app announcement"), make("p", "anm-muted", "Announcements appear in recipients' personal Notifications inboxes. They do not send email."));
  const form = make("form", "anm-form");
  const label = (caption, field) => { const holder = make("label", "anm-field"); holder.append(make("span", "", caption), field); return holder; };
  const titleInput = make("input", "anm-input"); titleInput.required = true; titleInput.maxLength = 200; titleInput.placeholder = "Announcement title";
  const messageInput = make("textarea", "anm-input"); messageInput.required = true; messageInput.maxLength = 2000; messageInput.rows = 5; messageInput.placeholder = "Write your announcement...";
  const audience = make("select", "anm-input");
  for (const [value, caption] of [["all","All active accounts"],["student","Students"],["lecturer","Lecturers"],["librarian","Librarians"],["admin","Administrators"]]) {
    const option = make("option", "", caption); option.value = value; audience.append(option);
  }
  const send = make("button", "anm-btn anm-primary", "Review announcement"); send.type = "submit";
  form.append(label("Title", titleInput), label("Message", messageInput), label("Audience", audience), send);
  compose.append(form); layout.append(compose);
  const guide = make("section", "anm-panel anm-guide");
  guide.append(make("h2", "", "How delivery works"), make("p", "", "Each active recipient receives a separate in-app notification. Users can mark their own notifications as read."),make("p", "", "Audience targeting uses each account's current role. Inactive accounts are excluded."), make("p", "", "Records below show individual notifications, not unique campaigns. A sent announcement cannot be recalled here."));
  layout.append(guide);

  const recordsPanel = make("section", "anm-panel");
  const recordsTitle = make("div", "anm-records-top");
  recordsTitle.append(make("h2", "", "Recent notification records"));
  const filter = make("select", "anm-input anm-filter");
  for (const [val, cap] of [["","All types"],["general","General / announcements"],["new_resource","New resources"],["resource_request","Resource requests"],["course_reading_list","Reading lists"],["system","System"]]) {
    const op = make("option", "", cap); op.value = val; filter.append(op);
  }
  recordsTitle.append(filter); recordsPanel.append(recordsTitle);
  const tableWrap = make("div", "anm-table-wrap");
  recordsPanel.append(tableWrap);
  const pager = make("div", "anm-pager");
  recordsPanel.append(pager);
  root.append(recordsPanel);
  let offset = 0;
  let generation = 0;

  form.addEventListener("submit", event => {
    event.preventDefault();
    const title = titleInput.value.trim(); const message = messageInput.value.trim();
    if (title.length < 3 || message.length < 5) { notice.textContent = "Enter a title of at least 3 characters and a message of at least 5 characters."; return; }
    const modal = make("div", "anm-overlay");
    const card = make("section", "anm-modal");
    card.setAttribute("role", "dialog"); card.setAttribute("aria-modal", "true");
    const summary = `Send “${title}” to ${audience.options[audience.selectedIndex].text}? This creates a notification for every active matching account.`;
    card.append(make("h2", "", "Confirm announcement"), make("p", "", summary));
    const actions = make("div", "anm-modal-actions");
    const close = () => modal.remove();
    const cancel = button("Cancel", close);
    const confirm = button("Send announcement", async () => {
      confirm.disabled = true; cancel.disabled = true;
      try {
        const data = await apiRequest("/admin/notifications/announcements", { method: "POST", body: JSON.stringify({title, message, audience: audience.value}) });
        notice.textContent = `Announcement delivered to ${data.recipient_count} in-app inbox${data.recipient_count === 1 ? "" : "es"}. No emails were sent.`;
        notice.className = "anm-feedback anm-success";
        form.reset(); close(); offset = 0; await refresh();
      } catch (error) { notice.textContent = error.message; notice.className = "anm-feedback anm-error"; confirm.disabled = false; cancel.disabled = false; }
    }, "anm-primary");
    actions.append(cancel, confirm); card.append(actions); modal.append(card); document.body.append(modal);
    cancel.focus();
    modal.addEventListener("click", e => { if(e.target === modal && !confirm.disabled) close(); });
    modal.addEventListener("keydown", e => { if(e.key === "Escape" && !confirm.disabled) close(); });
  });
  filter.addEventListener("change", () => {offset = 0; refreshRecords();});

  async function refreshRecords() {
    const current = ++generation;
    tableWrap.replaceChildren(make("p", "anm-muted", "Loading notification records…"));
    try {
      const query = new URLSearchParams({limit: "15", offset: String(offset)});
      if (filter.value) query.set("notification_type", filter.value);
      const data = await apiRequest(`/admin/notifications/records?${query}`);
      if (current !== generation || !root.isConnected) return;
      tableWrap.replaceChildren(); pager.replaceChildren();
      if (!data.items.length) { tableWrap.append(make("p", "anm-empty", "No notification records found.")); }
      else {
        const table = make("table", "anm-table");
        const thead = make("thead"); const headings = make("tr");
        for (const col of ["Notification", "Recipient", "Role", "Created", "Status"]) headings.append(make("th", "", col));
        thead.append(headings); table.append(thead);
        const tbody = make("tbody");
        for (const record of data.items) {
          const tr = make("tr");
          const first = make("td"); first.append(make("strong", "", record.title), make("span", "anm-type", pretty(record.notification_type)));
          tr.append(first, make("td", "", record.recipient_name), make("td", "", pretty(record.recipient_role)), make("td", "", formatDate(record.created_at)));
          const statusCell = make("td"); statusCell.append(make("span", record.is_read ? "anm-status read" : "anm-status unread", record.is_read ? "Read" : "Unread")); tr.append(statusCell); tbody.append(tr);
        }
        table.append(tbody); tableWrap.append(table);
      }
      const previous = button("← Previous", () => {offset = Math.max(0, offset - 15); refreshRecords();});
      previous.disabled = offset === 0;
      const next = button("Next →", () => {offset += 15; refreshRecords();});
      next.disabled = offset + 15 >= data.total;
      pager.append(previous, make("span", "", `Page ${Math.floor(offset/15)+1} · ${data.total} records`), next);
    } catch (error) { if(current === generation) tableWrap.replaceChildren(make("p", "anm-error", error.message)); }
  }
  async function refresh() {
    reload.disabled = true;
    try {
      const data = await apiRequest("/admin/notifications/overview");
      if (!root.isConnected) return;
      stats.replaceChildren();
      for (const [label, value] of [["Notification records",data.total_records],["Unread records",data.unread_records],["Active accounts",data.active_users],["General notifications",data.by_type?.general || 0]]) {
        const card = make("article", "anm-stat"); card.append(make("span", "", label), make("strong", "", String(value))); stats.append(card);
      }
    } catch (error) { stats.replaceChildren(make("p", "anm-error", error.message)); }
    finally { reload.disabled = false; }
    await refreshRecords();
  }
  await refresh();
}
