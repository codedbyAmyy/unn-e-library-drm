import { apiRequest } from './api.js';

const h = (tag, cls = '', text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = String(text);
  return node;
};
const btn = (label, click, cls = 'aum-btn aum-outline') => {
  const b = h('button', cls, label);
  b.type = 'button';
  b.addEventListener('click', click);
  return b;
};
const userDate = value => {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleDateString(undefined, {day:'numeric', month:'short', year:'numeric'});
};
const titleCase = word => word ? word.charAt(0).toUpperCase() + word.slice(1) : '—';

function openConfirmation({heading, detail, confirmLabel, dangerous=false, onConfirm}) {
  const backdrop = h('div', 'aum-backdrop');
  const dialog = h('section', 'aum-dialog');
  dialog.setAttribute('role', 'dialog'); dialog.setAttribute('aria-modal', 'true');
  const headingNode = h('h2', '', heading);
  const headingId = 'aum-dialog-heading'; headingNode.id = headingId;
  dialog.setAttribute('aria-labelledby', headingId);
  dialog.append(headingNode, h('p', 'aum-muted', detail));
  const message = h('p', 'aum-dialog-feedback');
  message.setAttribute('role', 'alert');
  const actions = h('div', 'aum-dialog-actions');
  const close = () => { document.removeEventListener('keydown', esc); backdrop.remove(); };
  const esc = e => { if (e.key === 'Escape') close(); };
  const cancel = btn('Cancel', close);
  const confirm = btn(confirmLabel, async () => {
    cancel.disabled = true; confirm.disabled = true; confirm.textContent = 'Saving…';
    try { await onConfirm(); close(); }
    catch (err) { message.textContent = err.message || 'Could not save changes.'; confirm.disabled = false; cancel.disabled = false; confirm.textContent = confirmLabel; }
  }, dangerous ? 'aum-btn aum-danger' : 'aum-btn aum-primary');
  actions.append(cancel, confirm);
  dialog.append(message, actions); backdrop.append(dialog);
  backdrop.addEventListener('click', e => { if (e.target === backdrop) close(); });
  document.addEventListener('keydown', esc);
  document.body.append(backdrop); cancel.focus();
}

export async function showAdminUserManagement({content, user}) {
  content.replaceChildren();
  const root = h('div','aum-page'); content.append(root);
  if (user?.role !== 'admin') { root.append(h('p','aum-error','Administrator access is required.')); return; }

  const top = h('div','aum-heading');
  const headline = h('div'); headline.append(h('p','aum-eyebrow','USER ADMINISTRATION'),h('h1','', 'User Management'),h('p','aum-muted','Review accounts, manage access, and assign permitted roles.'));
  const refresh = btn('↻ Refresh', () => load(), 'aum-btn aum-outline');
  top.append(headline,refresh); root.append(top);

  const tiles = h('div','aum-stat-grid'); root.append(tiles);
  const toolbar = h('form','aum-toolbar');
  const search = h('input','aum-input'); search.type='search'; search.placeholder='Search name, email, matric number or staff ID'; search.setAttribute('aria-label','Search accounts');
  const role = h('select','aum-input'); role.setAttribute('aria-label','Filter by role');
  for (const [v,t] of [['','All roles'],['student','Students'],['lecturer','Lecturers'],['librarian','Librarians'],['admin','Administrators']]) { const o=h('option','',t);o.value=v;role.append(o); }
  const status = h('select','aum-input');status.setAttribute('aria-label','Filter by status');
  for (const [v,t] of [['','All statuses'],['true','Active'],['false','Inactive']]) { const o=h('option','',t);o.value=v;status.append(o); }
  const searchBtn=h('button','aum-btn aum-primary','Search');searchBtn.type='submit';
  toolbar.append(search,role,status,searchBtn);root.append(toolbar);

  const info = h('div','aum-notice');info.setAttribute('role','status');root.append(info);
  const card = h('section','aum-table-card');
  const scroll = h('div','aum-table-scroll'); const table=h('table','aum-table');
  const thead=h('thead'),headerRow=h('tr');
  ['Account','Role','Academic Details','Joined','Status','Actions'].forEach(t=>headerRow.append(h('th','',t)));
  thead.append(headerRow); const tbody=h('tbody');table.append(thead,tbody);scroll.append(table);card.append(scroll);
  const pager = h('div','aum-pager');card.append(pager);root.append(card);
  let offset = 0;const limit=10;let requestNumber=0;

  function showTiles(data) {
    tiles.replaceChildren();
    const entries=[['Total accounts', data?.total],['Active accounts', data?.active],['Inactive accounts',data?.inactive]];
    for (const [label,value] of entries) {
      const tile=h('article','aum-stat');tile.append(h('p','aum-muted',label),h('strong','',value===null||value===undefined?'—':value));tiles.append(tile);
    }
  }

  async function saveChange(record, kind, value) {
    const url = kind==='role' ? `/admin/users/${record.id}/role` : `/admin/users/${record.id}/status`;
    const body = kind==='role' ? {role:value} : {is_active:value};
    await apiRequest(url,{method:'PATCH',body:JSON.stringify(body)});
    info.textContent=`${record.full_name}'s ${kind==='role'?'role':'account status'} was updated.`;
    await load(true);
  }

  function editRole(record) {
    const panel=h('div','aum-role-picker');
    const selection=h('select','aum-input');selection.setAttribute('aria-label','New role');
    for (const r of ['student','lecturer','librarian']) { const o=h('option','',titleCase(r));o.value=r;selection.append(o); }
    selection.value = ['student','lecturer','librarian'].includes(record.role) ? record.role : 'librarian';
    const note=h('p','aum-muted','Student and lecturer roles require the correct academic identity fields. The backend will reject incompatible changes.');
    panel.append(selection,note);
    const backdrop=h('div','aum-backdrop');const dialog=h('section','aum-dialog');dialog.setAttribute('role','dialog');dialog.setAttribute('aria-modal','true');
    const title=h('h2','',`Change role — ${record.full_name}`);title.id='aum-role-dialog-heading';dialog.setAttribute('aria-labelledby',title.id);dialog.append(title,panel);
    const feedback=h('p','aum-dialog-feedback');feedback.setAttribute('role','alert');dialog.append(feedback);
    const actions=h('div','aum-dialog-actions');
    const close=()=>{document.removeEventListener('keydown',esc);backdrop.remove();};
    const esc=e=>{if(e.key==='Escape')close();};
    const cancel=btn('Cancel',close);const save=btn('Save role',async()=>{
      if(selection.value===record.role){feedback.textContent='Select a different role.';return;}
      save.disabled=cancel.disabled=true;
      try{await saveChange(record,'role',selection.value);close();}
      catch(e){feedback.textContent=e.message;save.disabled=cancel.disabled=false;}
    },'aum-btn aum-primary');
    actions.append(cancel,save);dialog.append(actions);backdrop.append(dialog);backdrop.addEventListener('click',e=>{if(e.target===backdrop)close();});document.addEventListener('keydown',esc);document.body.append(backdrop);selection.focus();
  }

  function renderRows(rows) {
    tbody.replaceChildren();
    if (!rows.length) {const tr=h('tr');const td=h('td','aum-empty','No accounts match these filters.');td.colSpan=6;tr.append(td);tbody.append(tr);return;}
    for (const record of rows) {
      const tr=h('tr');
      const identity=h('td');identity.append(h('strong','aum-name',record.full_name||'Unnamed account'),h('span','aum-email',record.email||''));
      const roleCell=h('td');roleCell.append(h('span',`aum-chip aum-role-${record.role}`,titleCase(record.role)));
      const academic=h('td','aum-muted',[record.matric_number,record.staff_id,record.academic_level ? `${record.academic_level} Level` : ''].filter(Boolean).join(' · ')||'—');
      const joined=h('td','aum-muted',userDate(record.created_at));
      const account=h('td');account.append(h('span',`aum-chip ${record.is_active?'aum-active':'aum-inactive'}`,record.is_active?'Active':'Inactive'));
      const actions=h('td');const actionGroup=h('div','aum-row-actions');
      const view=btn('View',()=>{
        openConfirmation({heading:record.full_name,detail:`Email: ${record.email}\nRole: ${titleCase(record.role)}\nStatus: ${record.is_active?'Active':'Inactive'}\nRegistered: ${userDate(record.created_at)}`,confirmLabel:'Close',onConfirm:async()=>{}});
      });actionGroup.append(view);
      if(record.role !== 'admin' && record.id !== user.id) {
        actionGroup.append(btn('Change Role',()=>editRole(record)));
        const nextActive=!record.is_active;
        actionGroup.append(btn(nextActive?'Activate':'Deactivate',()=>openConfirmation({
          heading:`${nextActive?'Activate':'Deactivate'} ${record.full_name}?`,
          detail:nextActive?'This account will be allowed to sign in again.':'This account will be prevented from signing in. Existing sessions may remain valid until their token expires.',
          confirmLabel:nextActive?'Activate account':'Deactivate account',dangerous:!nextActive,
          onConfirm:()=>saveChange(record,'status',nextActive)
        }),nextActive?'aum-btn aum-outline':'aum-btn aum-warn'));
      }else actionGroup.append(h('span','aum-protected',record.id===user.id?'Your account':'Protected admin'));
      actions.append(actionGroup);tr.append(identity,roleCell,academic,joined,account,actions);tbody.append(tr);
    }
  }

  async function load(keepNotice=false) {
    const current=++requestNumber;
    if(!keepNotice)info.textContent='Loading accounts…';
    tbody.replaceChildren();pager.replaceChildren();
    try {
      const params=new URLSearchParams({limit:String(limit),offset:String(offset)});
      if(search.value.trim())params.set('search',search.value.trim());
      if(role.value)params.set('role',role.value);
      if(status.value)params.set('is_active',status.value);
      const [data,overview] = await Promise.all([
        apiRequest(`/admin/users?${params}`),
        Promise.allSettled([
          apiRequest('/admin/users?limit=1&offset=0'),
          apiRequest('/admin/users?is_active=true&limit=1&offset=0'),
          apiRequest('/admin/users?is_active=false&limit=1&offset=0')
        ])
      ]);
      if(current!==requestNumber)return;
      const values=overview.map(x=>x.status==='fulfilled'?x.value.total:null);
      showTiles({total:values[0],active:values[1],inactive:values[2]});
      renderRows(data.items||[]);
      const total=Number(data.total||0);
      if(!keepNotice)info.textContent=`Showing ${total===0?0:offset+1}–${Math.min(offset+limit,total)} of ${total} matching accounts`;
      const prev=btn('← Previous',()=>{offset=Math.max(0,offset-limit);load();});prev.disabled=offset===0;
      const next=btn('Next →',()=>{offset+=limit;load();});next.disabled=offset+limit>=total;
      pager.append(prev,h('span','',`Page ${Math.floor(offset/limit)+1}`),next);
    } catch(e) { if(current!==requestNumber)return;info.textContent=e.message||'Could not load accounts.';info.classList.add('aum-error'); }
  }
  toolbar.addEventListener('submit',e=>{e.preventDefault();offset=0;load();});
  role.addEventListener('change',()=>{offset=0;load();});
  status.addEventListener('change',()=>{offset=0;load();});
  await load();
}
