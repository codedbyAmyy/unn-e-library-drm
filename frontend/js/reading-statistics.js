import { apiRequest } from './api.js';

const el = (tag, cls = '', text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = String(text);
  return n;
};
const fmt = (s) => {
  const mins = Math.floor(Math.max(0, s) / 60);
  return mins >= 60 ? `${Math.floor(mins / 60)}h ${mins % 60}m` : `${mins} min`;
};
const date = (s) => {
  const d = new Date(s);
  return Number.isNaN(d.valueOf()) ? 'Unknown date' : d.toLocaleDateString(undefined, {month:'short',day:'numeric',year:'numeric'});
};

export async function showReadingStatistics({ content, openPdf, showDetails }) {
  const root = el('section', 'unn-stats');
  root.append(el('p','unn-stats-eyebrow','MY READING ACTIVITY'), el('h1','unn-stats-title','Reading Statistics'),
    el('p','unn-stats-subtitle','Your reading habits and progress, based on saved library activity.'));
  const metrics = el('div','unn-stats-metrics');
  const summary = el('p','unn-stats-note','Loading your reading records…');
  const grid = el('div','unn-stats-main');
  const history = el('section','unn-stats-panel');
  const breakdown = el('section','unn-stats-panel');
  history.append(el('h2','','Recent reading progress'));
  breakdown.append(el('h2','','Resource types in your history'));
  grid.append(history,breakdown);
  root.append(metrics,summary,grid);
  content.append(root);
  try {
    const [result, totals] = await Promise.all([
      apiRequest('/reading-history?limit=100&offset=0'),
      apiRequest('/reading-statistics/me')
    ]);
    const entries = Array.isArray(result) ? result : (result.items || []);
    const distinctIds = [...new Set(entries.map(e => Number(e.resource_id)).filter(id => Number.isInteger(id) && id > 0))];
    // Fetch only most recent resources to keep the page responsive.
    const ids = distinctIds.slice(0,12);
    const details = new Map();
    const progress = new Map();
    await Promise.all(ids.map(async id=>{
      const [d,p] = await Promise.allSettled([
        apiRequest(`/resources/${id}`), apiRequest(`/reading-progress/${id}`)
      ]);
      if (d.status === 'fulfilled') details.set(id,d.value);
      if (p.status === 'fulfilled') progress.set(id,p.value);
    }));
    // Completion totals are computed across ALL saved progress records on the server.
    const cards = [
      ['Reading records',totals.reading_records,'All saved history records'],
      ['Unique resources',totals.unique_resources,'Across all saved reading history'],
      ['Recorded reading time',fmt(totals.recorded_duration_seconds),'Recorded duration across all history entries'],
      ['Completed PDFs',totals.completed_pdfs,`Across all ${totals.tracked_pdfs} saved PDF positions`]
    ];
    for (const [label,value,note] of cards) {
      const c = el('article','unn-stats-metric');
      c.append(el('p','',label),el('strong','',value),el('small','',note));
      metrics.append(c);
    }
    summary.textContent = `Summary figures cover all saved records. Showing the latest ${entries.length} of ${totals.reading_records} reading records for recent activity, with page progress for up to ${ids.length} resources. Reading time includes only duration actually recorded.`;
    const list = el('div','unn-stats-list');
    if (!ids.length) list.append(el('p','unn-stats-empty','No reading records yet. Open a protected PDF to start tracking your progress.'));
    for (const id of ids) {
      const r = details.get(id), p = progress.get(id);
      const entry = entries.find(x=>Number(x.resource_id)===id);
      const pct = p?.total_pages>0 ? Math.min(100, Math.round(p.current_page / p.total_pages * 100)) : null;
      const row = el('article','unn-stats-resource');
      const top = el('div','unn-stats-resource-top');
      top.append(el('strong','',r?.title || 'Resource unavailable'),el('span','',date(entry?.last_read_at || entry?.started_at)));
      row.append(top, el('p','unn-stats-muted',pct === null ? 'No page position saved' : `Page ${p.current_page} of ${p.total_pages} · ${pct}% reached`));
      const track = el('div','unn-stats-track');
      const fill = el('span'); fill.style.width=`${pct??0}%`;
      track.append(fill);row.append(track);
      if (r) {
        const actions = el('div','unn-stats-actions');
        if (typeof openPdf === 'function') { const b=el('button','unn-stats-button','Continue reading'); b.type='button';b.addEventListener('click',()=>openPdf(id));actions.append(b); }
        if (typeof showDetails === 'function') {const b=el('button','unn-stats-button secondary','View details');b.type='button';b.addEventListener('click',()=>showDetails(id));actions.append(b);}
        row.append(actions);
      }
      list.append(row);
    }
    history.append(list);
    const types = new Map();
    for (const r of details.values()) { const type=(r.resource_type||'other').replaceAll('_',' ');types.set(type,(types.get(type)||0)+1); }
    if (!types.size) breakdown.append(el('p','unn-stats-empty','Resource types will appear once you have reading history.'));
    else for (const [type,count] of [...types].sort((a,b)=>b[1]-a[1])) {
      const line=el('div','unn-stats-category');
      const head=el('div','unn-stats-category-head');head.append(el('span','',type),el('strong','',count));line.append(head);
      const bar=el('div','unn-stats-track');const fill=el('span');fill.style.width=`${Math.round(count/details.size*100)}%`;bar.append(fill);line.append(bar);breakdown.append(line);
    }
    breakdown.append(el('p','unn-stats-footnote','Categories represent resource types among recently loaded accessible resources, not academic departments.'));
  } catch(e) {
    summary.textContent = `Unable to load reading statistics: ${e.message}`;
    summary.setAttribute('role','alert');
  }
}
