import { apiRequest } from './api.js';

const TYPES = {
  file_unavailable: 'Missing or unavailable file',
  file_corrupted: 'Corrupted PDF',
  incorrect_metadata: 'Incorrect metadata',
  access_problem: 'Access problem',
  other: 'Other issue',
};
const STATES = {open:'Open',under_review:'In Progress',resolved:'Resolved',dismissed:'Dismissed'};
const h=(tag,cls='',value='')=>{const x=document.createElement(tag);if(cls)x.className=cls;if(value!==undefined)x.textContent=String(value);return x;};
const btn=(text,primary=false)=>{const b=h('button',primary?'brf-btn brf-primary':'brf-btn',text);b.type='button';return b;};
const date=v=>v?new Date(v).toLocaleDateString(undefined,{day:'2-digit',month:'short',year:'numeric'}):'—';
function select(values,label){const s=h('select','brf-select');s.setAttribute('aria-label',label);for(const [value,name] of values){const o=h('option','',name);o.value=value;s.append(o);}return s;}
function badge(state){return h('span',`brf-badge brf-${state}`,STATES[state]||state||'Unknown');}
function field(text,control){const l=h('label','brf-field');l.append(h('span','',text),control);return l;}

// Use the existing paginated endpoint; do not invent server search or aggregate APIs.
async function fetchReports(){const items=[];let total=0;for(let offset=0;offset<2000;offset+=100){const data=await apiRequest(`/reports?limit=100&offset=${offset}`);total=data.total||0;items.push(...(data.items||[]));if(items.length>=total||!(data.items||[]).length)break;}return {items,total,partial:items.length<total};}

export async function showLibrarianReportsPage({content}){
  const root=h('section','brf-page');content.replaceChildren(root);
  const header=h('header','brf-heading');header.append(h('p','brf-kicker','RESOURCE QUALITY & ACCESS'),h('h1','','Broken Resource Reports'),h('p','brf-subtitle','Investigate inaccessible, missing or damaged digital resources and track resolutions.'));root.append(header);
  const feedback=h('p','brf-feedback');feedback.setAttribute('role','status');root.append(feedback);
  const stats=h('section','brf-stats');stats.setAttribute('aria-label','Report statistics');root.append(stats);
  const panel=h('section','brf-panel');panel.append(h('h2','','Reported Resource Issues'),h('p','brf-subtitle','Review reported problems and update their resolution progress.'));
  const controls=h('div','brf-controls');const search=h('input','brf-input');search.type='search';search.placeholder='Search resource title or issue…';search.setAttribute('aria-label','Search reports');
  const kind=select([['','All issue types'],...Object.entries(TYPES)],'Filter by issue type');const status=select([['','All statuses'],...Object.entries(STATES)],'Filter by status');const sort=select([['new','Newest first'],['old','Oldest first']],'Sort reports');controls.append(search,kind,status,sort);panel.append(controls);
  const tableWrap=h('div','brf-table-wrap');const pager=h('div','brf-pagination');panel.append(tableWrap,pager);root.append(panel);
  const detail=h('section','brf-detail');detail.hidden=true;root.append(detail);
  let reports=[],total=0,partial=false,page=0;const size=8;const resources=new Map();
  function resourceName(id){return resources.get(id)?.title || 'Resource details unavailable';}
  function drawStats(){stats.replaceChildren();for(const [title,val,note,state] of [
    ['Total Reports',total,'All submitted issues','all'],
    ['Open Reports',reports.filter(r=>r.status==='open').length,'Awaiting review','open'],
    ['In Progress',reports.filter(r=>r.status==='under_review').length,'Being investigated','under_review'],
    ['Resolved',reports.filter(r=>r.status==='resolved').length,'Issues successfully closed','resolved']]){
      const card=h('article','brf-stat');card.append(h('span','brf-stat-label',title),h('strong','',`${val}${partial&&state!=='all'?'+':''}`),h('small','',note));stats.append(card);
    }
  }
  function filtered(){const q=search.value.trim().toLocaleLowerCase();return reports.filter(r=>(!kind.value||kind.value===r.issue_type)&&(!status.value||status.value===r.status)&&(!q||[resourceName(r.resource_id),TYPES[r.issue_type],r.description,String(r.id)].some(x=>String(x||'').toLocaleLowerCase().includes(q)))).sort((a,b)=>sort.value==='old'?new Date(a.created_at)-new Date(b.created_at):new Date(b.created_at)-new Date(a.created_at));}
  function draw(){const rows=filtered();const pages=Math.max(1,Math.ceil(rows.length/size));page=Math.min(page,pages-1);tableWrap.replaceChildren();const table=h('table','brf-table');const head=h('thead');const tr=h('tr');for(const txt of ['RESOURCE / REPORT','REPORTED BY','ISSUE TYPE','DATE','STATUS','ACTION'])tr.append(h('th','',txt));head.append(tr);table.append(head);const body=h('tbody');for(const r of rows.slice(page*size,(page+1)*size)){const row=h('tr');const resource=h('td');resource.append(h('strong','',resourceName(r.resource_id)),h('small','',`Report ${String(r.id).padStart(4,'0')}`));const who=h('td','','Library account');const issue=h('td','',TYPES[r.issue_type]||r.issue_type);const when=h('td','',date(r.created_at));const st=h('td');st.append(badge(r.status));const action=h('td');const b=btn(['open','under_review'].includes(r.status)?'Review Report':'View Details',['open','under_review'].includes(r.status));b.onclick=()=>showDetails(r);action.append(b);row.append(resource,who,issue,when,st,action);body.append(row);}table.append(body);tableWrap.append(table);if(!rows.length)tableWrap.append(h('p','brf-empty','No reports match your filters.'));pager.replaceChildren();const previous=btn('← Previous');previous.disabled=page===0;previous.onclick=()=>{page--;draw();};const next=btn('Next →');next.disabled=page>=pages-1;next.onclick=()=>{page++;draw();};pager.append(h('span','',`Showing ${rows.length?page*size+1:0}–${Math.min((page+1)*size,rows.length)} of ${rows.length}${partial?' loaded':''}`),previous,h('span','',`Page ${page+1} of ${pages}`),next);}
  function showDetails(r){detail.hidden=false;detail.replaceChildren();const top=h('div','brf-detail-header');top.append(h('h2','','Review Resource Report'));const close=btn('Close');close.onclick=()=>{detail.hidden=true;};top.append(close);detail.append(top);
    const dl=h('dl','brf-meta');for(const [k,v] of [['Resource',resourceName(r.resource_id)],['Issue type',TYPES[r.issue_type]],['Reported on',date(r.created_at)],['Status',STATES[r.status]],['Issue description',r.description||'No additional description'],['Resolution notes',r.resolution_notes]]){if(v){dl.append(h('dt','',k),h('dd','',v));}}detail.append(dl);
    if(!['open','under_review'].includes(r.status))return;
    const form=h('form','brf-form');const options=r.status==='open'?[['','Select outcome'],['under_review','Begin investigation'],['resolved','Mark resolved'],['dismissed','Dismiss report']]:[['','Select outcome'],['resolved','Mark resolved'],['dismissed','Dismiss report']];const decision=select(options,'Report decision');decision.required=true;const notes=h('textarea','brf-input');notes.rows=4;notes.maxLength=2000;notes.placeholder='Explain how the issue was resolved or why it was dismissed';const message=h('p','brf-feedback');message.setAttribute('role','status');const save=btn('Save decision',true);save.type='submit';form.append(field('Decision',decision),field('Resolution notes',notes),message,save);form.onsubmit=async ev=>{ev.preventDefault();if(!decision.value)return;if(['resolved','dismissed'].includes(decision.value)&&!notes.value.trim()){message.textContent='Please enter resolution notes before closing this report.';return;}save.disabled=true;message.textContent='Saving…';try{await apiRequest(`/reports/${r.id}/review`,{method:'PATCH',body:JSON.stringify({status:decision.value,resolution_notes:notes.value.trim()||null})});detail.hidden=true;feedback.textContent='Report updated successfully.';await reload();}catch(err){message.textContent=err.message;}finally{save.disabled=false;}};detail.append(form);detail.scrollIntoView({behavior:'smooth',block:'nearest'});
  }
  async function loadResourceNames(){const ids=[...new Set(reports.map(r=>r.resource_id))].slice(0,100);await Promise.all(ids.map(async id=>{try{resources.set(id,await apiRequest(`/resources/${id}`));}catch{resources.set(id,{title:'Resource unavailable'});}}));}
  async function reload(){try{const data=await fetchReports();reports=data.items;total=data.total;partial=data.partial;await loadResourceNames();drawStats();draw();if(partial)feedback.textContent=`Displaying ${reports.length} of ${total} reports; server-side search is needed to cover a larger catalogue.`;}catch(err){stats.replaceChildren();tableWrap.replaceChildren(h('p','brf-error',`Could not load reports: ${err.message}`));}}
  const change=()=>{page=0;draw();};search.addEventListener('input',change);kind.addEventListener('change',change);status.addEventListener('change',change);sort.addEventListener('change',change);
  stats.append(h('p','brf-subtitle','Loading report statistics…'));tableWrap.append(h('p','brf-subtitle','Loading reports…'));await reload();
}
