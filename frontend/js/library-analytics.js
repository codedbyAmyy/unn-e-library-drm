import { apiRequest } from "./api.js";

const mk = (tag, className = "", text = null) => {
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (text !== null) e.textContent = String(text);
  return e;
};
const num = (n) => Number(n || 0).toLocaleString();
const cap = (s) => String(s || "Other").replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
const shortDate = (s) => {
  if (!s) return "—";
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleDateString(undefined, {year:"numeric",month:"short",day:"numeric"});
};
function nav(target) { window.location.hash = `#${target}`; }
function groupBy(items, key) {
  const result = new Map();
  items.forEach(x => result.set(key(x), (result.get(key(x)) || 0) + 1));
  return [...result.entries()].sort((a,b) => b[1] - a[1]);
}
async function allResources() {
  const all = [];
  let offset = 0;
  while (true) {
    const data = await apiRequest(`/resources?limit=100&offset=${offset}`);
    const items = Array.isArray(data) ? data : (data.items || []);
    all.push(...items);
    const total = Number(data.total ?? all.length);
    if (!items.length || all.length >= total) {
      if (all.length < total) throw new Error("Catalogue records could not be fully retrieved.");
      return {rows:all, total};
    }
    offset += items.length;
  }
}
async function totalUsers(role, isActive) {
  const p = new URLSearchParams({limit:"1",offset:"0"});
  if (role) p.set("role",role);
  if (isActive !== undefined) p.set("is_active",String(isActive));
  const data = await apiRequest(`/admin/users?${p}`);
  return Number(data.total || 0);
}
function metric(label, value, description) {
  const cell=mk("article","unn-analytics-metric");
  cell.append(mk("span","unn-analytics-metric-label",label),mk("strong","unn-analytics-metric-value",num(value)),mk("small","unn-analytics-muted",description));
  return cell;
}
function section(title, subtitle) {
  const box=mk("section","unn-analytics-panel");
  const h=mk("div","unn-analytics-section-heading");
  h.append(mk("h2","",title),mk("p","unn-analytics-muted",subtitle));
  box.append(h);return box;
}
function bars(entries, emptyText="No records available") {
  const outer=mk("div","unn-analytics-bars");
  if (!entries.length) {outer.append(mk("p","unn-analytics-muted",emptyText));return outer;}
  const max=Math.max(1,...entries.map(x=>x[1]));
  for (const [name,value] of entries) {
    const item=mk("div","unn-analytics-bar-item"),top=mk("div","unn-analytics-bar-label");
    top.append(mk("span","",cap(name)),mk("strong","",num(value)));
    const track=mk("div","unn-analytics-bar-track"),fill=mk("span","unn-analytics-bar-fill");
    fill.style.width=`${Math.max(0,(value/max)*100)}%`;track.append(fill);
    item.append(top,track);outer.append(item);
  }
  return outer;
}
function trend(resources) {
  const counts = new Map();
  for (const r of resources) {
    const d=new Date(r.created_at);
    if (Number.isNaN(d.getTime())) continue;
    const month=`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}`;
    counts.set(month,(counts.get(month)||0)+1);
  }
  const months = [...counts.entries()].sort((a,b)=>a[0].localeCompare(b[0]));
  return months.slice(-12).map(([ym,count])=>[new Date(`${ym}-01T00:00:00`).toLocaleDateString(undefined,{month:"short",year:"numeric"}),count]);
}
function resourcesTable(resources) {
  const wrap=mk("div","unn-analytics-table-scroll"),table=mk("table","unn-analytics-table");
  const thead=mk("thead"),head=mk("tr");
  ["Resource","Type","Uploaded","Status"].forEach(x=>head.append(mk("th","",x)));
  thead.append(head);table.append(thead);
  const tbody=mk("tbody");
  const latest=resources.slice().sort((a,b)=>String(b.created_at||"").localeCompare(String(a.created_at||""))).slice(0,8);
  for (const r of latest) {
    const row=mk("tr"),title=mk("td");
    title.append(mk("strong","",r.title||"Untitled"));
    row.append(title,mk("td","",cap(r.resource_type)),mk("td","",shortDate(r.created_at)));
    const status=r.is_archived?"Archived":r.is_published?"Published":"Draft";
    const td=mk("td"),badge=mk("span",`unn-analytics-status ${status.toLowerCase()}`,status);
    td.append(badge);row.append(td);tbody.append(row);
  }
  if (!latest.length){const tr=mk("tr"),td=mk("td","unn-analytics-muted","No resources yet.");td.colSpan=4;tr.append(td);tbody.append(tr);}
  table.append(tbody);wrap.append(table);return wrap;
}
export async function showLibraryAnalytics({ content, user } = {}) {
  if (!content) throw new Error("Analytics content container missing.");
  content.replaceChildren();
  const root=mk("div","unn-analytics");content.append(root);
  const header=mk("header","unn-analytics-header"),intro=mk("div");
  intro.append(mk("p","unn-analytics-eyebrow","ADMINISTRATION  /  LIVE LIBRARY DATA"),mk("h1","","Library Analytics"),mk("p","unn-analytics-muted","Catalogue composition, account distribution and resource-upload activity."));
  const refresh=mk("button","unn-analytics-button","Refresh data");refresh.type="button";
  header.append(intro,refresh);root.append(header);
  if (user?.role !== "admin") {root.append(mk("p","unn-analytics-error","Only administrators can view library analytics."));refresh.disabled=true;return;}
  const body=mk("div","unn-analytics-body");root.append(body);
  let generation=0;
  async function load(){
    const current=++generation;
    body.replaceChildren(mk("p","unn-analytics-muted","Loading verified library figures…"));refresh.disabled=true;
    try {
      const [catalogue,users,active,student,lecturer,librarian,admin] = await Promise.all([
        allResources(), totalUsers(), totalUsers(undefined,true),totalUsers("student"),totalUsers("lecturer"),totalUsers("librarian"),totalUsers("admin")
      ]);
      if(current!==generation || !root.isConnected) return;
      const rows=catalogue.rows;
      const published=rows.filter(r=>r.is_published && !r.is_archived).length;
      const drafts=rows.filter(r=>!r.is_archived && !r.is_published).length;
      const archived=rows.filter(r=>r.is_archived).length;
      const summary=mk("div","unn-analytics-metrics");
      summary.append(metric("Total Resources",catalogue.total,"All accessible catalogue records"),metric("Published Resources",published,"Currently available to readers"),metric("Registered Accounts",users,"All roles combined"),metric("Active Accounts",active,"Currently allowed to sign in"));
      const panels=mk("div","unn-analytics-panels");
      const statusPanel=section("Publication Status","All catalogue records, including drafts and archives");
      statusPanel.append(bars([["Published",published],["Draft",drafts],["Archived",archived]]));
      const typePanel=section("Resource Types","Distribution across all catalogue records");
      typePanel.append(bars(groupBy(rows,r=>r.resource_type||"other")));
      const rolePanel=section("Accounts by Role","Live account totals from administrator records");
      rolePanel.append(bars([["Student",student],["Lecturer",lecturer],["Librarian",librarian],["Administrator",admin]]));
      const trendPanel=section("Uploads Over Time","Latest 12 months containing recorded uploads; zero-activity months omitted");
      trendPanel.append(bars(trend(rows),"No upload dates available."));
      panels.append(statusPanel,typePanel,rolePanel,trendPanel);
      const recent=section("Recently Uploaded Resources","Latest eight catalogue records, including unpublished and archived resources");
      recent.append(resourcesTable(rows));
      const bottom=mk("div","unn-analytics-footer");
      bottom.append(mk("span","unn-analytics-muted","All figures refresh from the current database. Upload trends use resource creation dates, not reading or download events."));
      const toUsers=mk("button","unn-analytics-secondary","Manage users"),toResources=mk("button","unn-analytics-secondary","Browse resources");
      [toUsers,toResources].forEach(b=>b.type="button");toUsers.onclick=()=>nav("users");toResources.onclick=()=>nav("resources-admin");
      bottom.append(toUsers,toResources);
      body.replaceChildren(summary,panels,recent,bottom);
    } catch(e) {
      if(current!==generation || !root.isConnected) return;
      const msg=mk("div","unn-analytics-error");msg.setAttribute("role","alert");
      msg.append(mk("strong","","Unable to load analytics"),mk("p","",e.message||String(e)));
      body.replaceChildren(msg);
    } finally {if(current===generation && root.isConnected) refresh.disabled=false;}
  }
  refresh.addEventListener("click",load);
  await load();
}
