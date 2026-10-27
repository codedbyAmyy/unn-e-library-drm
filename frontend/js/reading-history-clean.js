import { apiRequest } from './api.js';
const make=(tag,cls='',text='')=>{const e=document.createElement(tag);if(cls)e.className=cls;e.textContent=text;return e;};
const rid=x=>Number(x.resource_id ?? x.resource?.id ?? x.id);
const latest=x=>x.last_read_at||x.started_at||x.created_at||'';
const date=x=>{const d=new Date(x);return Number.isNaN(d.getTime())?'Date unavailable':d.toLocaleString();};
export async function showReadingHistoryClean({content,openPdf,showDetails}){
  const root=make('section','rh-clean');
  root.append(make('h1','','Reading History'),make('p','rh-sub','Your recently accessed academic resources.'));
  const list=make('div','rh-list'),pager=make('nav','rh-pager');pager.setAttribute('aria-label','Reading history pages');
  root.append(list,pager);content.append(root);
  list.append(make('p','','Loading reading history…'));
  try{
    const records=[];let offset=0,limit=100;
    // Fetch complete history so pagination applies to distinct resources, not repeated visits.
    while(true){
      const result=await apiRequest(`/reading-history?limit=${limit}&offset=${offset}`);
      const items=Array.isArray(result)?result:(result.items||[]);
      records.push(...items);
      const total=Number(result.total??records.length);
      if(!items.length||records.length>=total)break;
      offset+=items.length;
    }
    const byId=new Map();
    for(const entry of records){const id=rid(entry);if(!Number.isInteger(id)||id<=0)continue;
      const previous=byId.get(id);
      if(!previous||String(latest(entry))>String(latest(previous)))byId.set(id,entry);
    }
    const distinct=[...byId.values()].sort((a,b)=>String(latest(b)).localeCompare(String(latest(a))));
    let page=0;const pageSize=6;
    async function showPage(){
      list.replaceChildren();pager.replaceChildren();
      const subset=distinct.slice(page*pageSize,(page+1)*pageSize);
      if(!distinct.length){list.append(make('p','rh-empty','No reading history yet. Open a protected PDF to get started.'));return;}
      const results=await Promise.all(subset.map(async entry=>{
        const id=rid(entry);
        try{const r=await apiRequest(`/resources/${id}`);return {entry,id,resource:r};}
        catch{return {entry,id,resource:null};}
      }));
      for(const {entry,id,resource:r} of results){
        if(!r)continue;
        const card=make('article','rh-card');
        card.append(make('span','rh-tag',(r.resource_type||'Resource').replaceAll('_',' ')),make('h2','',r.title||'Academic resource'),make('p','rh-muted',`Last accessed: ${date(latest(entry))}`));
        const progress=make('p','rh-muted','Checking saved page progress…');card.append(progress);
        const track=make('div','rh-track'),fill=make('span','rh-fill');track.append(fill);card.append(track);
        try{const p=await apiRequest(`/reading-progress/${id}`);
          if(p?.total_pages>0&&p?.current_page>0){const pct=Math.min(100,Math.round(p.current_page/p.total_pages*100));progress.textContent=`Page ${p.current_page} of ${p.total_pages} · ${pct}% reached`;fill.style.width=pct+'%';}
          else progress.textContent='No page position saved yet.';
        }catch{progress.textContent='Page progress unavailable.';}
        const actions=make('div','rh-actions');
        for(const [label,fn,style] of [['Continue reading',()=>openPdf(id),'rh-primary'],['View details',()=>showDetails(id),'rh-secondary']]){
          const b=make('button',style,label);b.type='button';b.onclick=fn;actions.append(b);
        }
        card.append(actions);list.append(card);
      }
      if(!list.children.length)list.append(make('p','rh-empty','No accessible resources on this page.'));
      const prev=make('button','','← Previous'),next=make('button','','Next →');
      prev.disabled=page===0;next.disabled=(page+1)*pageSize>=distinct.length;
      prev.onclick=()=>{page--;void showPage();};next.onclick=()=>{page++;void showPage();};
      pager.append(prev,make('span','',`Page ${page+1} of ${Math.ceil(distinct.length/pageSize)}`),next);
    }
    await showPage();
  }catch(e){list.replaceChildren(make('p','rh-empty',`Could not load reading history: ${e.message}`));}
}
