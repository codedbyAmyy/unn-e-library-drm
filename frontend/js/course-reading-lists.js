import { apiRequest } from './api.js';
import { confirmAction } from './ui-dialog.js';

const E=(tag,cls='',text='')=>{const n=document.createElement(tag);if(cls)n.className=cls;n.textContent=text;return n;};
const B=(label,fn,quiet=false)=>{const b=E('button',quiet?'btn-quiet':'btn-primary-alt',label);b.type='button';b.addEventListener('click',fn);return b;};
const field=(label,kind='text',required=false)=>{const l=E('label','crl-field');l.append(E('span','',label));const i=kind==='textarea'?E('textarea'):E('input','field-input');if(kind!=='textarea')i.type=kind;i.required=required;l.append(i);return {l,i};};
const academicSessionField=(selected='')=>{
  const l=E('label','crl-field');l.append(E('span','','Academic session (optional)'));
  const i=E('select','field-input');
  const blank=E('option','','Select academic session');blank.value='';i.append(blank);
  for(let year=2021;year<=2034;year++){
    const value=`${year}/${year+1}`;const option=E('option','',value);option.value=value;i.append(option);
  }
  if(selected && ![...i.options].some(o=>o.value===selected)){
    const saved=E('option','',`${selected} (previously saved)`);saved.value=selected;i.append(saved);
  }
  i.value=selected||'';l.append(i);return {l,i};
};
const reader=id=>{const url=new URL('./reader.html',location.href);url.searchParams.set('resource',String(id));const w=window.open(url.href,'_blank');if(!w) location.href=url.href;};
const details=id=>{location.hash='#library'; /* Library discovery is the supported fallback route. */};
function explain(err){return err?.message||'Could not complete this action.';}
export async function showCourseReadingLists({user,content}){
  const editor=user.role==='lecturer'||user.role==='librarian';
  const h=E('div','page-heading');h.append(E('h1','',editor?'Course Reading Lists · Manage':'Course Reading Lists'),E('p','subheading',editor?'Create course reading lists and publish them for eligible students.':'Find course reading lists available to you and open the assigned resources.'));content.append(h);
  const notice=E('p','crl-feedback');notice.setAttribute('role','status');notice.setAttribute('aria-live','polite');content.append(notice);
  const root=E('section','data-panel');content.append(root);
  const toolbar=E('div','crl-toolbar');root.append(toolbar);
  const course=E('select','field-input');course.setAttribute('aria-label','Filter by course');
  const coursesById=new Map();
  const describeCourse=id=>{const c=coursesById.get(Number(id));return c?`${c.course_code} — ${c.title}`:`Course unavailable`;};
  const courseOption=(c)=>{const option=E('option','',`${c.course_code} — ${c.title}${c.academic_level?' · '+c.academic_level+' Level':''}`);option.value=String(c.id);return option;};
  async function loadCourses(){
    try{
      const records=await api('/academic/courses');
      coursesById.clear();for(const c of records)coursesById.set(Number(c.id),c);
      course.replaceChildren();const all=E('option','','All courses');all.value='';course.append(all);
      for(const c of records)course.append(courseOption(c));
      if(!records.length)feedback('No courses in the academic catalogue yet. Add confirmed courses first.');
    }catch(e){feedback('Could not load courses: '+explain(e),true);}
  }
  toolbar.append(course,B('Find lists',()=>{offset=0;void load();}));
  if(editor)toolbar.append(B('+ Create reading list',()=>createForm()));
  const listing=E('div','crl-grid');root.append(listing);const pager=E('div','crl-pagination');root.append(pager);
  let offset=0;const limit=20;
  const feedback=(msg,isError=false)=>{notice.textContent=msg;notice.classList.toggle('crl-error',isError)};
  const api=(url,method='GET',body)=>apiRequest(url,{method,...(body?{body:JSON.stringify(body)}:{})});
  function actionCall(url,method,body,success){return api(url,method,body).then(()=>{feedback(success);return load();}).catch(e=>feedback(explain(e),true));}
  async function load(){
    listing.replaceChildren(E('p','crl-muted','Loading course reading lists…'));pager.replaceChildren();
    const q=new URLSearchParams({limit:String(limit),offset:String(offset)});
    if(course.value)q.set('course_id',course.value);
    try{const d=await api(`/reading-lists?${q}`);listing.replaceChildren();const items=d.items||[];
      if(!items.length)listing.append(E('p','crl-muted','No reading lists are available for this selection.'));
      for(const r of items){const c=E('article','crl-card');const top=E('div','crl-actions');const tag=E('span',`crl-badge ${r.is_published?'':'draft'}`,r.is_published?'Published':'Draft');top.append(tag);c.append(top,E('h3','',r.title),E('p','crl-muted',`${describeCourse(r.course_id)}${r.academic_session?' · '+r.academic_session:''} · ${(r.items||[]).length} resource(s)`));if(r.description)c.append(E('p','crl-muted',r.description));c.append(B('View reading list',()=>void view(r.id),true));listing.append(c);}
      const previous=B('← Previous',()=>{offset=Math.max(0,offset-limit);void load();},true);previous.disabled=offset===0;
      const next=B('Next →',()=>{offset+=limit;void load();},true);next.disabled=offset+limit>=d.total;
      pager.append(previous,E('span','',`Page ${Math.floor(offset/limit)+1} · ${d.total} total`),next);
    }catch(e){listing.replaceChildren(E('p','crl-error',explain(e)));}
  }
  function createForm(){
    root.querySelector('.crl-create')?.remove();const form=E('form','crl-form crl-create');
    const cid=field('Course *','text',true);
    const oldInput=cid.i;const picker=E('select','field-input');picker.required=true;
    const placeholder=E('option','','Select a course');placeholder.value='';picker.append(placeholder);
    for(const c of coursesById.values())picker.append(courseOption(c));
    oldInput.replaceWith(picker);const title=field('Reading list title *','text',true);title.i.maxLength=200;
    const session=academicSessionField();const desc=field('Description','textarea');
    const response=E('p','crl-feedback');const submit=E('button','btn-primary-alt','Create draft');submit.type='submit';
    form.append(cid.l,title.l,session.l,desc.l,response,submit,B('Close',()=>form.remove(),true));root.insertBefore(form,listing);
    form.addEventListener('submit',async ev=>{ev.preventDefault();const id=Number(picker.value);if(!Number.isSafeInteger(id)||id<=0){response.textContent='Please select a course.';return;}
      submit.disabled=true;response.textContent='Creating draft…';try{const r=await api('/reading-lists','POST',{course_id:id,title:title.i.value.trim(),academic_session:session.i.value.trim()||null,description:desc.i.value.trim()||null});form.remove();feedback('Draft created. Add published resources before publishing.');await load();await view(r.id);}catch(e){response.textContent=explain(e);}finally{submit.disabled=false;}
    });picker.focus();
  }
  async function view(id){
    listing.hidden=true;pager.hidden=true;toolbar.hidden=true;root.querySelector('.crl-create')?.remove();const previous=root.querySelector('.crl-detail');previous?.remove();
    const section=E('div','crl-detail');root.append(section);section.append(E('p','crl-muted','Loading reading list…'));
    try{
      const r=await api(`/reading-lists/${id}`);section.replaceChildren();section.append(E('h2','',r.title),E('p','crl-muted',`${describeCourse(r.course_id)} · ${r.academic_session||'Session not specified'} · ${r.is_published?'Published':'Draft'}`));
      if(r.description)section.append(E('p','crl-muted',r.description));
      const canEdit=editor&&(user.role==='librarian'||r.created_by===user.id);
      const actions=E('div','crl-actions');section.append(actions);
      actions.append(B('← All reading lists',()=>{section.remove();listing.hidden=false;pager.hidden=false;toolbar.hidden=false;void load();},true));
      if(canEdit){
        if(r.is_published)actions.append(B('Unpublish list',async()=>{if(await confirmAction({title:'Unpublish reading list?',message:'Students will no longer be able to access this list until you publish it again.',confirmText:'Unpublish'}))await actionCall(`/reading-lists/${id}/unpublish`,'POST',null,'List unpublished.').then(()=>view(id));},true));
        else{
          actions.append(B('Edit details',()=>editForm(section,r)));
          actions.append(B('Publish list',async()=>{if(await confirmAction({title:'Publish reading list?',message:'Publish this list with its currently assigned resources?',confirmText:'Publish'}))await actionCall(`/reading-lists/${id}/publish`,'POST',null,'List published.').then(()=>view(id));}));
          actions.append(B('Add resource',()=>addForm(section,r)));
        }
      }
      const entries=E('div','crl-items');section.append(entries);
      if(!r.items?.length)entries.append(E('p','crl-muted','No resources added yet.'));
      for(const item of [...(r.items||[])].sort((a,b)=>a.position-b.position)){
        const c=E('article','crl-item');const name=E('h3','',`Resource #${item.resource_id}`);c.append(name);
        if(item.notes)c.append(E('p','crl-muted',item.notes));if(item.is_required)c.append(E('span','crl-badge','Required'));
        try {const resource=await api(`/resources/${item.resource_id}`);name.textContent=resource.title; if(resource.authors?.length)c.append(E('p','crl-muted',resource.authors.map(a=>typeof a==='string'?a:a.author_name).join(', ')));}
        catch {c.append(E('p','crl-muted','Resource details unavailable.'));}
        const controls=E('div','crl-actions');controls.append(B('Read protected PDF',()=>reader(item.resource_id)));
        if(canEdit&&!r.is_published)controls.append(B('Remove',async()=>{if(await confirmAction({title:'Remove resource?',message:'Remove this resource from the draft reading list?',confirmText:'Remove',danger:true})){try{await api(`/reading-lists/${id}/items/${item.id}`,'DELETE');feedback('Resource removed.');await view(id);}catch(e){feedback(explain(e),true);}}},true));
        c.append(controls);entries.append(c);
      }
    }catch(e){section.replaceChildren(E('p','crl-error',explain(e)),B('← Back',()=>{section.remove();listing.hidden=false;pager.hidden=false;toolbar.hidden=false;},true));}
  }
  function editForm(section,r){section.querySelector('.crl-editor')?.remove();const form=E('form','crl-form crl-editor');const title=field('Title','text',true);title.i.value=r.title;title.i.maxLength=200;const desc=field('Description','textarea');desc.i.value=r.description||'';const session=academicSessionField(r.academic_session||'');const msg=E('p','crl-feedback');const submit=E('button','btn-primary-alt','Save changes');submit.type='submit';form.append(title.l,desc.l,session.l,msg,submit,B('Close',()=>form.remove(),true));section.insertBefore(form,section.querySelector('.crl-items'));form.addEventListener('submit',async e=>{e.preventDefault();submit.disabled=true;try{await api(`/reading-lists/${r.id}`,'PATCH',{title:title.i.value.trim(),description:desc.i.value.trim()||null,academic_session:session.i.value.trim()||null});feedback('Reading list updated.');await view(r.id);}catch(err){msg.textContent=explain(err);submit.disabled=false;}});}
  function addForm(section,r){
    section.querySelector('.crl-editor')?.remove();
    const form=E('form','crl-form crl-editor');
    const search=field('Find a published resource by title, author, ISBN or DOI','search');
    search.i.placeholder='Search the library catalogue';
    const searchButton=B('Search resources',()=>void findResources());
    const results=E('div','crl-search-results');
    const selection=E('p','crl-muted','No resource selected yet.');
    const notes=field('Notes for students','textarea');
    const line=E('label','crl-check');
    const required=E('input');required.type='checkbox';
    line.append(required,E('span','','Required reading'));
    const msg=E('p','crl-feedback');
    const submit=E('button','btn-primary-alt','Add selected resource');
    submit.type='submit';submit.disabled=true;
    let selected=null;let searchOffset=0;const searchLimit=20;
    const searchPaging=E('div','crl-pagination');
    form.append(search.l,searchButton,results,searchPaging,selection,notes.l,line,msg,submit,B('Close',()=>form.remove(),true));
    section.insertBefore(form,section.querySelector('.crl-items'));
    async function findResources(){
      results.replaceChildren(E('p','crl-muted','Searching library…'));
      searchPaging.replaceChildren();msg.textContent='';
      const q=new URLSearchParams({limit:String(searchLimit),offset:String(searchOffset)});
      const term=search.i.value.trim();if(term){q.set('search',term);q.set('search_field','all');}
      try{
        const data=await api(`/resources?${q}`);
        results.replaceChildren();
        const rows=(data.items||[]).filter(item=>item.is_published&&!item.is_archived);
        if(!rows.length)results.append(E('p','crl-muted','No published resources on this page. Try a different search.'));
        for(const item of rows){
          const row=E('div','crl-picker-row');
          const authors=(item.authors||[]).map(a=>typeof a==='string'?a:a.author_name||a.name||'').filter(Boolean).join(', ');
          const choose=B('Select',()=>{
            selected=item;selection.textContent=`Selected: ${item.title}${authors?' — '+authors:''}`;
            submit.disabled=false;
            for(const button of results.querySelectorAll('button'))button.setAttribute('aria-pressed',button===choose?'true':'false');
          },true);
          choose.setAttribute('aria-pressed',selected?.id===item.id?'true':'false');
          row.append(E('strong','',item.title),E('p','crl-muted',`${authors||item.resource_type||'Academic resource'}${item.publication_year?' · '+item.publication_year:''}`),choose);
          results.append(row);
        }
        const prev=B('← Previous',()=>{searchOffset-=searchLimit;void findResources();},true);
        prev.disabled=searchOffset===0;
        const next=B('Next →',()=>{searchOffset+=searchLimit;void findResources();},true);
        next.disabled=searchOffset+searchLimit>=data.total;
        searchPaging.append(prev,E('span','',`Page ${Math.floor(searchOffset/searchLimit)+1}`),next);
      }catch(err){results.replaceChildren();msg.textContent=explain(err);}
    }
    search.i.addEventListener('input',()=>{selected=null;submit.disabled=true;selection.textContent='No resource selected yet.';searchOffset=0;});
    search.i.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();searchOffset=0;void findResources();}});
    form.addEventListener('submit',async event=>{
      event.preventDefault();if(!selected){msg.textContent='Search for and select a published resource first.';return;}
      submit.disabled=true;
      try{
        await api(`/reading-lists/${r.id}/items`,'POST',{resource_id:selected.id,notes:notes.i.value.trim()||null,is_required:required.checked});
        feedback('Resource added to reading list.');await view(r.id);
      }catch(err){msg.textContent=explain(err);submit.disabled=false;}
    });
    void findResources();search.i.focus();
  }

  await loadCourses();
  await load();
}
