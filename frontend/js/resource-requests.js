import { apiRequest } from './api.js';
import { confirmAction } from './ui-dialog.js';

const statuses = ['pending', 'under_review', 'approved', 'fulfilled', 'rejected', 'cancelled'];
const allowed = {
  pending: ['under_review', 'approved', 'rejected'],
  under_review: ['approved', 'rejected'],
  approved: ['fulfilled', 'rejected'],
  fulfilled: [], rejected: [], cancelled: []
};
const labels = {pending:'Pending',under_review:'Under review',approved:'Approved',fulfilled:'Fulfilled',rejected:'Rejected',cancelled:'Cancelled'};
const kinds = ['book','journal','article','thesis','dissertation','lecture_note','conference_paper','research_paper','report','other'];
const elem = (tag, className = '', text = '') => {
  const e = document.createElement(tag);
  if (className) e.className = className;
  e.textContent = text;
  return e;
};
function btn(text, onClick, className = 'btn-primary-alt') {
  const e = elem('button', className, text); e.type = 'button'; e.addEventListener('click', onClick); return e;
}
function inputField(label, {type='text',maxLength,required=false,options,rows} = {}) {
  const wrap = elem('label','request-field'); wrap.append(elem('span','',label));
  const field = options ? elem('select','field-input') : rows ? elem('textarea','field-input') : elem('input','field-input');
  if (!options && !rows) field.type = type;
  if (maxLength) field.maxLength = maxLength;
  field.required = required;
  if (rows) field.rows = rows;
  if (options) for(const [value,title] of options){const o=elem('option','',title);o.value=value;field.append(o);}
  wrap.append(field); return {wrap,field};
}
function formatted(iso) { if(!iso) return '—';const d=new Date(iso);return Number.isNaN(d.getTime()) ? String(iso) : d.toLocaleString(); }
function statusPill(value){return elem('span',`request-status request-status--${value}`,labels[value]||value||'Unknown');}
function explain(err){ return err?.message || 'Please try again.'; }
function openReader(resourceId) {
  const u=new URL('./reader.html',window.location.href);
  u.searchParams.set('resource',String(resourceId));
  const w=window.open(u.href,'_blank');
  if (!w) window.location.href=u.href;
}
function itemCard(record, asLibrarian, refresh) {
  const card=elem('article','request-record');
  const top=elem('div','request-record-top');
  top.append(elem('h3','',record.title || `Request #${record.id}`),statusPill(record.status));card.append(top);
  const details=elem('div','request-details');
  for(const [key,value] of [
    ['Type',record.resource_type?.replaceAll('_',' ')],['Author',record.author],
    ['Requested',formatted(record.created_at)],['Request ID',record.id],
    ...(asLibrarian ? [['Requester ID',record.requested_by]] : []),
    ['Notes',record.description],['Reason',record.reason],['Librarian response',record.review_notes],
    ['Reviewed',record.reviewed_at ? formatted(record.reviewed_at) : null]
  ]) if(value!==null && value!==undefined && value!==''){details.append(elem('dt','',key),elem('dd','',String(value)));}
  card.append(details);
  const buttons=elem('div','request-actions');
  if(record.status==='fulfilled' && record.fulfilled_resource_id){
    buttons.append(btn('Read available resource',()=>openReader(record.fulfilled_resource_id)));
  }
  if(!asLibrarian && record.status==='pending') {
    buttons.append(btn('Cancel request',async()=>{
      if(!(await confirmAction({title:'Cancel resource request?',message:`Cancel your request for “${record.title}”? This cannot be undone.`,confirmText:'Cancel request',danger:true}))) return;
      try{await apiRequest(`/requests/${record.id}/cancel`,{method:'POST'});await refresh('Request cancelled.');}
      catch(e){const note=elem('p','request-feedback',explain(e));note.setAttribute('role','alert');card.append(note);}
    },'btn-quiet'));
  }
  if(asLibrarian){
    const transitions=allowed[record.status]||[];
    if(transitions.length)buttons.append(btn('Review request',()=>showReviewForm(card,record,transitions,refresh),'btn-primary-alt'));
  }
  if(buttons.childElementCount)card.append(buttons);
  return card;
}
function showReviewForm(card,record,transitions,refresh){
  card.querySelector('.request-review')?.remove();
  const form=elem('form','request-review');
  const action=inputField('Decision',{options:[['','Select a decision'],...transitions.map(s=>[s,labels[s]])],required:true});
  const notes=inputField('Response to requester (required for rejection)',{rows:3,maxLength:2000});
  const fulfilled=inputField('Published resource ID (required for fulfilment)',{type:'number'});
  fulfilled.field.min='1';
  fulfilled.wrap.hidden=true;
  action.field.addEventListener('change',()=>{fulfilled.wrap.hidden=action.field.value!=='fulfilled';notes.field.required=action.field.value==='rejected';});
  const feedback=elem('p','request-feedback');feedback.setAttribute('role','status');
  const submit=elem('button','btn-primary-alt','Save decision');submit.type='submit';
  const cancel=btn('Cancel',()=>form.remove(),'btn-quiet');
  const controls=elem('div','request-actions');controls.append(cancel,submit);
  form.append(action.wrap,notes.wrap,fulfilled.wrap,feedback,controls);
  form.addEventListener('submit',async e=>{
    e.preventDefault();
    const status=action.field.value;
    if(!transitions.includes(status)){feedback.textContent='Choose a valid decision.';return;}
    const payload={status,review_notes:notes.field.value.trim()||null};
    if(status==='rejected'&&!payload.review_notes){feedback.textContent='Explain the rejection to the requester.';return;}
    if(status==='fulfilled'){
      const id=Number(fulfilled.field.value);
      if(!Number.isSafeInteger(id)||id<=0){feedback.textContent='Enter a valid published resource ID.';return;}
      payload.fulfilled_resource_id=id;
    }
    submit.disabled=true;cancel.disabled=true;feedback.textContent='Saving decision…';
    try{await apiRequest(`/requests/${record.id}/review`,{method:'PATCH',body:JSON.stringify(payload)});await refresh('Request updated successfully.');}
    catch(err){feedback.textContent=explain(err);submit.disabled=false;cancel.disabled=false;}
  });
  card.append(form);action.field.focus();
}
export async function showResourceRequests({user,content}) {
  const librarian=user.role==='librarian';
  const requester=['student','lecturer'].includes(user.role);
  if(!librarian && !requester){content.append(elem('p','error-state','You do not have access to resource requests.'));return;}
  const header=elem('div','page-heading');header.append(elem('h1','',librarian?'Process Resource Requests':'Resource Requests'),elem('p','subheading',librarian?'Review requests, record decisions and connect fulfilled requests to published resources.':'Request materials that are not in the library, and track the librarian response.'));content.append(header);
  const notice=elem('p','request-feedback');notice.setAttribute('role','status');notice.setAttribute('aria-live','polite');content.append(notice);
  if(requester){
    const panel=elem('section','data-panel');panel.append(elem('h2','panel-heading','Request a resource'));
    const form=elem('form','request-create-form');
    const title=inputField('Resource title *',{required:true,maxLength:300});
    const author=inputField('Author (if known)',{maxLength:200});
    const type=inputField('Resource type *',{required:true,options:kinds.map(v=>[v,v.replaceAll('_',' ')])});
    const reason=inputField('Why do you need this resource?',{rows:3,maxLength:2000});
    const description=inputField('Additional information (optional)',{rows:2,maxLength:2000});
    const status=elem('p','request-feedback');status.setAttribute('role','status');
    const submit=elem('button','btn-primary-alt','Submit request');submit.type='submit';
    form.append(title.wrap,author.wrap,type.wrap,reason.wrap,description.wrap,status,submit);panel.append(form);content.append(panel);
    form.addEventListener('submit',async e=>{
      e.preventDefault();submit.disabled=true;status.textContent='Submitting request…';
      try{
        await apiRequest('/requests',{method:'POST',body:JSON.stringify({title:title.field.value.trim(),author:author.field.value.trim()||null,resource_type:type.field.value,reason:reason.field.value.trim()||null,description:description.field.value.trim()||null})});
        form.reset();status.textContent='Request submitted successfully.';offset=0;await load();
      }catch(err){status.textContent=explain(err);}finally{submit.disabled=false;}
    });
  }
  const results=elem('section','data-panel');results.append(elem('h2','panel-heading',librarian?'Incoming requests':'Your requests'));
  const filters=elem('div','request-filters');
  const statusSelect=inputField('Filter by status',{options:[['','All statuses'],...statuses.map(s=>[s,labels[s]])]});
  filters.append(statusSelect.wrap);results.append(filters);
  const listing=elem('div','request-list');results.append(listing);
  const pager=elem('div','pager');results.append(pager);content.append(results);
  let offset=0;const limit=20;
  statusSelect.field.addEventListener('change',()=>{offset=0;void load();});
  async function load(success=''){
    listing.replaceChildren(elem('p','empty-state','Loading requests…'));pager.replaceChildren();
    if(success)notice.textContent=success;
    const p=new URLSearchParams({limit:String(limit),offset:String(offset)});
    if(statusSelect.field.value)p.set('status',statusSelect.field.value);
    try{
      const data=await apiRequest(`/requests?${p}`);
      listing.replaceChildren();
      const items=data.items||[];
      if(!items.length)listing.append(elem('p','empty-state','No requests match this filter.'));
      else for(const r of items)listing.append(itemCard(r,librarian,load));
      const prev=btn('← Previous',()=>{offset=Math.max(0,offset-limit);void load();},'btn-quiet');prev.disabled=offset===0;
      const next=btn('Next →',()=>{offset+=limit;void load();},'btn-quiet');next.disabled=offset+limit>=data.total;
      pager.append(prev,elem('span','',`Page ${Math.floor(offset/limit)+1} · ${data.total} total`),next);
    }catch(err){listing.replaceChildren(elem('p','error-state',explain(err)));}
  }
  await load();
}
